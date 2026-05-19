package org.demo.controller;

import org.demo.entity.ChatHistory;
import org.demo.entity.ChatSession;
import org.demo.entity.Result;
import org.demo.service.ChatService;
import org.demo.utils.ThreadLocalUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.util.UriComponentsBuilder;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;

@RestController
@RequestMapping("/chat")

public class ChatController {

    @Autowired
    private ChatService chatService;

    @Value("${ai.server.base-url:http://localhost:5000}")
    private String aiServerBaseUrl;

    private final RestTemplate restTemplate;{
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10000);
        factory.setReadTimeout(600000);  // 5分钟
        restTemplate = new RestTemplate(factory);
    }

    private Long getCurrentUserId() {
        Map<String, Object> claims = ThreadLocalUtil.get();
        return Long.valueOf(claims.get("id").toString());
    }

    /**
     * 发送消息（问答核心接口）
     */
    @PostMapping("/send")
    public Result<Map<String, Object>> sendMessage(@RequestBody Map<String, Object> body) {
        String question = (String) body.get("question");
        String sessionId = (String) body.get("sessionId");
        // 接收联网搜索开关参数
        Boolean useSearch = body.get("useSearch") != null && (Boolean) body.get("useSearch");
        // 接收语义缓存开关参数
        Boolean useCache = body.get("useCache") != null ? (Boolean) body.get("useCache") : true;
        // 接收选中的知识库文件列表
        @SuppressWarnings("unchecked")
        List<String> selectedKnowledgeBases = (List<String>) body.get("selectedKnowledgeBases");

        Long currentUserId = getCurrentUserId();

        if (question == null || question.trim().isEmpty()) {
            return Result.error("问题不能为空");
        }

        try {
            String activeSessionId = chatService.getOrCreateSession(currentUserId, sessionId);
            // 传递所有参数到 service 层
            ChatHistory history = chatService.processChat(
                    currentUserId,
                    activeSessionId,
                    question,
                    useSearch,
                    useCache,
                    selectedKnowledgeBases
            );
            Map<String, Object> resp = new HashMap<>();
            resp.put("sessionId", activeSessionId);
            resp.put("answer", history.getLlmResponse());
            resp.put("think", history.getThinkContent() == null ? "" : history.getThinkContent());
            resp.put("source", history.getSource() != null ? history.getSource() : "rag");
            return Result.success(resp);
        } catch (Exception e) {
            e.printStackTrace();
            return Result.error("处理消息时发生错误：" + e.getMessage());
        }
    }

    /**
     * 获取某个会话的聊天历史
     */
    @GetMapping("/history")
    public Result<List<ChatHistory>> getHistory(@RequestParam String sessionId) {
        Long currentUserId = getCurrentUserId();
        return Result.success(chatService.getHistory(currentUserId, sessionId));
    }

    /**
     * 获取当前用户的所有会话列表
     */
    @GetMapping("/sessions")
    public Result<List<ChatSession>> getSessions() {
        Long currentUserId = getCurrentUserId();
        return Result.success(chatService.getUserSessions(currentUserId));
    }

    /**
     * 删除某个会话及其所有聊天记录
     */
    @DeleteMapping("/sessions/{sessionId}")
    public Result<Void> deleteSession(@PathVariable String sessionId) {
        Long currentUserId = getCurrentUserId();
        chatService.deleteSession(currentUserId, sessionId);
        return Result.success();
    }

    /**
     * 重置数据库（清空所有会话、聊天记录和知识库）
     */
    @PostMapping("/reset")
    public Result<Void> resetDatabase() {
        Long currentUserId = getCurrentUserId();
        try {
            // 调用 Python 端清空知识库和缓存
            ResponseEntity<Map> response = restTemplate.postForEntity(
                    aiServerBaseUrl + "/api/reset",
                    null,
                    Map.class
            );

            Map responseBody = response.getBody();
            if (responseBody != null && Integer.valueOf(200).equals(responseBody.get("code"))) {
                // Python 端清空成功后，清空当前用户的会话和聊天记录
                chatService.resetUserData(currentUserId);
                return Result.success();
            } else {
                String msg = responseBody != null ? (String) responseBody.get("msg") : "重置失败";
                return Result.error(msg);
            }
        } catch (Exception e) {
            e.printStackTrace();
            return Result.error("重置数据库失败：" + e.getMessage());
        }
    }

    /**
     * 上传文件到知识库（转发到 Python 端）
     */
    @PostMapping("/upload")
    public Result<Map<String, Object>> uploadFile(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return Result.error("文件不能为空");
        }

        try {
            // 构建 multipart 请求转发到 Python
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);

            // 将 MultipartFile 转为 ByteArrayResource
            ByteArrayResource resource = new ByteArrayResource(file.getBytes()) {
                @Override
                public String getFilename() {
                    return file.getOriginalFilename();
                }
            };

            MultiValueMap<String, Object> formData = new LinkedMultiValueMap<>();
            formData.add("file", new HttpEntity<>(resource, createFileHeaders(file)));

            HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(formData, headers);

            ResponseEntity<Map> response = restTemplate.exchange(
                    aiServerBaseUrl + "/api/upload",
                    HttpMethod.POST,
                    requestEntity,
                    Map.class
            );

            Map responseBody = response.getBody();
            if (responseBody != null && Integer.valueOf(200).equals(responseBody.get("code"))) {
                return Result.success((Map<String, Object>) responseBody.get("data"));
            } else {
                String msg = responseBody != null ? (String) responseBody.get("msg") : "上传失败";
                return Result.error(msg);
            }
        } catch (Exception e) {
            e.printStackTrace();
            return Result.error("文件上传失败：" + e.getMessage());
        }
    }


    /**
     * 获取知识库文件列表（转发到 Python 端）
     */
    @GetMapping("/files")
    public Result<Map<String, Object>> listFiles() {
        try {
            ResponseEntity<Map> response = restTemplate.getForEntity(
                    aiServerBaseUrl + "/api/list_files", Map.class);
            Map responseBody = response.getBody();
            if (responseBody != null && Integer.valueOf(200).equals(responseBody.get("code"))) {
                return Result.success((Map<String, Object>) responseBody.get("data"));
            }
            return Result.error("获取文件列表失败");
        } catch (Exception e) {
            e.printStackTrace();
            return Result.error("获取文件列表失败：" + e.getMessage());
        }
    }


    /**
     * 删除知识库文件（转发到 Python 端）
     */
    @DeleteMapping("/files")
    public Result<Void> deleteFile(@RequestParam String fileName) {
        if (fileName == null || fileName.trim().isEmpty()) {
            return Result.error("fileName 不能为空");
        }

        try {
            // 防止前端误传已编码字符串（如 %E8...）
            String decodedFileName = URLDecoder.decode(fileName, StandardCharsets.UTF_8);

            String url = UriComponentsBuilder
                    .fromHttpUrl(aiServerBaseUrl + "/api/delete_file")
                    .queryParam("file_name", decodedFileName)
                    .toUriString();

            ResponseEntity<Map> response = restTemplate.exchange(
                    url, HttpMethod.DELETE, HttpEntity.EMPTY, Map.class
            );

            Map responseBody = response.getBody();
            if (responseBody != null && Integer.valueOf(200).equals(responseBody.get("code"))) {
                return Result.success();
            }

            String msg = responseBody != null ? (String) responseBody.get("msg") : "删除失败";
            return Result.error(msg);
        } catch (Exception e) {
            e.printStackTrace();
            return Result.error("删除文件失败：" + e.getMessage());
        }
    }


    /**
     * 获取语义缓存统计信息（转发到 Python 端）
     */
    @GetMapping("/cache/stats")
    public Result<Map<String, Object>> getCacheStats() {
        try {
            ResponseEntity<Map> response = restTemplate.getForEntity(
                    aiServerBaseUrl + "/api/cache/stats", Map.class);
            Map responseBody = response.getBody();
            if (responseBody != null && Integer.valueOf(200).equals(responseBody.get("code"))) {
                return Result.success((Map<String, Object>) responseBody.get("data"));
            }
            return Result.error("获取缓存统计失败");
        } catch (Exception e) {
            return Result.error("获取缓存统计失败：" + e.getMessage());
        }
    }

    /**
     * 创建文件上传的 Content-Disposition 头
     */
    private HttpHeaders createFileHeaders(MultipartFile file) {
        HttpHeaders fileHeaders = new HttpHeaders();
        fileHeaders.setContentType(MediaType.parseMediaType(
                file.getContentType() != null ? file.getContentType() : "application/octet-stream"));
        return fileHeaders;
    }
}