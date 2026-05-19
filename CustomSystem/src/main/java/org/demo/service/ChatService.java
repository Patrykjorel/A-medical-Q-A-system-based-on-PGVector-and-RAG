package org.demo.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import org.demo.entity.ChatHistory;
import org.demo.entity.ChatSession;
import org.demo.mapper.ChatHistoryMapper;
import org.demo.mapper.ChatSessionMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.transaction.annotation.Transactional;

import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class ChatService {

    @Autowired
    private ChatHistoryMapper historyMapper;

    @Autowired
    private ChatSessionMapper sessionMapper;

    @Value("${ai.server.base-url:http://localhost:5000}")
    private String aiServerBaseUrl;

    private static final Pattern THINK_PATTERN =
            Pattern.compile("(?is)<think>(.*?)</think>");

    private record ThinkParseResult(String answer, String think) {}

    private final RestTemplate restTemplate;{
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10000);
        factory.setReadTimeout(300000);  // 5分钟
        restTemplate = new RestTemplate(factory);
    }

    /**
     * 创建或获取会话
     * - sessionId 为空：创建新会话
     * - sessionId 不为空：先校验该会话是否属于当前用户，存在则复用，不存在则新建
     */
    public String getOrCreateSession(Long userId, String sessionId) {
        if (sessionId != null && !sessionId.trim().isEmpty()) {
            QueryWrapper<ChatSession> sessionQuery = new QueryWrapper<>();
            sessionQuery.eq("session_id", sessionId);
            sessionQuery.eq("user_id", userId);

            ChatSession existing = sessionMapper.selectOne(sessionQuery);
            if (existing != null) {
                return sessionId;
            }
        }
        return createNewSession(userId);
    }

    private String createNewSession(Long userId) {
        String newSessionId = UUID.randomUUID().toString();
        ChatSession session = new ChatSession();
        session.setSessionId(newSessionId);
        session.setUserId(userId);
        session.setSessionName("新对话");
        session.setCreatedTime(LocalDateTime.now());
        sessionMapper.insert(session);
        return newSessionId;
    }

    /**
     * 根据第一条消息更新会话名称
     */
    private void updateSessionNameIfNeeded(String sessionId, String question) {
        QueryWrapper<ChatHistory> countQuery = new QueryWrapper<>();
        countQuery.eq("session_id", sessionId);
        Long count = historyMapper.selectCount(countQuery);

        if (count == 0) {
            String name = question.length() > 30 ? question.substring(0, 30) + "..." : question;
            UpdateWrapper<ChatSession> updateWrapper = new UpdateWrapper<>();
            updateWrapper.eq("session_id", sessionId);
            updateWrapper.set("session_name", name);
            sessionMapper.update(null, updateWrapper);
        }
    }

    private ThinkParseResult parseThinkAndAnswer(String rawAnswer, String thinkFromPython) {
        String answer = rawAnswer == null ? "" : rawAnswer.trim();
        String think = thinkFromPython == null ? "" : thinkFromPython.trim();

        // Python 已经返回 think，直接用
        if (!think.isEmpty()) {
            return new ThinkParseResult(answer, think);
        }

        // 兜底：从 answer 中拆 <think>...</think>
        Matcher matcher = THINK_PATTERN.matcher(answer);
        StringBuilder thinkBuilder = new StringBuilder();

        while (matcher.find()) {
            String part = matcher.group(1);
            if (part != null && !part.trim().isEmpty()) {
                if (thinkBuilder.length() > 0) thinkBuilder.append("\n\n");
                thinkBuilder.append(part.trim());
            }
        }

        if (thinkBuilder.length() > 0) {
            answer = matcher.replaceAll("").trim();
            think = thinkBuilder.toString();
        } else {
            think = "";
        }

        return new ThinkParseResult(answer, think);
    }

    /**
     * 核心问答逻辑
     * @param userId 用户ID
     * @param sessionId 会话ID
     * @param question 用户问题
     * @param useSearch 是否启用联网搜索
     * @param useCache 是否启用语义缓存
     * @param selectedKnowledgeBases 选中的知识库文件列表
     * @return 聊天历史记录
     */

    @Transactional(rollbackFor = Exception.class)
    public ChatHistory processChat(Long userId, String sessionId, String question,
                                   boolean useSearch, boolean useCache,
                                   List<String> selectedKnowledgeBases) {

        // 如果是新会话的第一条消息，更新会话名称
        updateSessionNameIfNeeded(sessionId, question);

        // 取出最近 N 轮历史（每轮对应 1 条 ChatHistory：一问一答），避免上下文过长；N 由 chat.history.max-rounds 配置，默认 10
        int limit = Math.max(1, Math.min(100, chatHistoryMaxRounds));
        QueryWrapper<ChatHistory> historyQuery = new QueryWrapper<>();
        historyQuery.eq("session_id", sessionId);
        historyQuery.orderByDesc("created_time");
        historyQuery.last("LIMIT 3");
        List<ChatHistory> recentHistories = historyMapper.selectList(historyQuery);
        java.util.Collections.reverse(recentHistories); // 翻转按时间正序排列

        // 构建历史记录列表
        java.util.List<Map<String, String>> historyList = new java.util.ArrayList<>();
        for (ChatHistory h : recentHistories) {
            historyList.add(Map.of("role", "user", "content", h.getUserInput()));
            historyList.add(Map.of("role", "assistant", "content", h.getLlmResponse()));
        }

        // 准备请求 Python 的参数
        Map<String, Object> pythonRequest = new HashMap<>();
        pythonRequest.put("question", question);
        pythonRequest.put("sessionId", sessionId);
        pythonRequest.put("userId", userId);
        pythonRequest.put("use_search", useSearch);  // 传递联网搜索开关
        pythonRequest.put("use_cache", useCache);    // 传递语义缓存开关
        pythonRequest.put("selected_knowledge_bases", selectedKnowledgeBases);  // 传递选中的知识库
        pythonRequest.put("history", historyList);  // 将历史记录传给 Python

        // 调用 Python 端
        Map<String, Object> pythonResponse = null;
        try {
            Map result = restTemplate.postForObject(aiServerBaseUrl + "/api/ask", pythonRequest, Map.class);
            if (result != null && result.containsKey("data")) {
                pythonResponse = (Map<String, Object>) result.get("data");
            }
        } catch (Exception e) {
            e.printStackTrace();
            throw new RuntimeException("AI 服务连接失败，请检查 Python 服务是否启动。地址: " + aiServerBaseUrl);
        }

        if (pythonResponse == null) {
            throw new RuntimeException("AI 服务返回为空");
        }

        // 解析结果
        String rawAnswer = pythonResponse.get("answer") == null ? "" : pythonResponse.get("answer").toString();
        String thinkFromPython = pythonResponse.get("think") == null ? "" : pythonResponse.get("think").toString();
        String source = pythonResponse.get("source") == null ? "rag" : pythonResponse.get("source").toString();

        ThinkParseResult parsed = parseThinkAndAnswer(rawAnswer, thinkFromPython);
        String answer = parsed.answer();
        String think = parsed.think();

        // 保存历史记录到 MySQL
        ChatHistory history = new ChatHistory();
        history.setSessionId(sessionId);
        history.setUserId(userId);
        history.setUserInput(question);
        history.setLlmResponse(answer);
        history.setThinkContent(think);
        history.setSource(source != null ? source : "rag");
        history.setCreatedTime(LocalDateTime.now());

        historyMapper.insert(history);

        return history;
    }

    /**
     * 获取历史记录
     */
    public List<ChatHistory> getHistory(Long userId, String sessionId) {
        QueryWrapper<ChatHistory> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("session_id", sessionId);
        queryWrapper.eq("user_id", userId);
        queryWrapper.orderByAsc("created_time");
        return historyMapper.selectList(queryWrapper);
    }

    /**
     * 获取用户所有会话
     */
    public List<ChatSession> getUserSessions(Long userId) {
        QueryWrapper<ChatSession> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("user_id", userId);
        queryWrapper.orderByDesc("created_time");
        return sessionMapper.selectList(queryWrapper);
    }

    /**
     * 删除会话及其聊天记录
     */
    public void deleteSession(Long userId, String sessionId) {
        // 先验证会话属于当前用户
        QueryWrapper<ChatSession> sessionQuery = new QueryWrapper<>();
        sessionQuery.eq("session_id", sessionId);
        sessionQuery.eq("user_id", userId);
        ChatSession session = sessionMapper.selectOne(sessionQuery);

        if (session == null) {
            throw new RuntimeException("会话不存在或无权操作");
        }

        // 删除聊天记录
        QueryWrapper<ChatHistory> historyQuery = new QueryWrapper<>();
        historyQuery.eq("session_id", sessionId);
        historyMapper.delete(historyQuery);

        // 删除会话
        sessionMapper.delete(sessionQuery);
    }

    /**
     * 重置用户数据（清空该用户的所有会话和聊天记录）
     * @param userId 用户ID
     */
    public void resetUserData(Long userId) {
        // 删除该用户的所有聊天记录
        QueryWrapper<ChatHistory> historyQuery = new QueryWrapper<>();
        historyQuery.eq("user_id", userId);
        historyMapper.delete(historyQuery);

        // 删除该用户的所有会话
        QueryWrapper<ChatSession> sessionQuery = new QueryWrapper<>();
        sessionQuery.eq("user_id", userId);
        sessionMapper.delete(sessionQuery);

        System.out.println("已清空用户 " + userId + " 的所有数据");
    }
}