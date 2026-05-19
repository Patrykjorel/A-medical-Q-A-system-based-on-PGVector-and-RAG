package org.demo.controller;

import org.demo.entity.Result;
import org.demo.entity.User;
import org.demo.service.UserService;
import org.demo.utils.JwtUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import jakarta.validation.constraints.Pattern;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/user")

@Validated
public class UserController {

    @Autowired
    private UserService userService;

    @PostMapping("/register")
    public Result register(
            @Pattern(regexp = "^\\S{1,30}$") String username,
            @Pattern(regexp = "^\\S{5,16}$") String password) {

        User user = userService.findByUserName(username);
        if (user != null) {
            return Result.error("用户名已被占用");
        }
        userService.register(username, password);
        return Result.success();
    }

    @PostMapping("/login")
    public Result<String> login(
            @Pattern(regexp = "^\\S{1,30}$") String username,
            @Pattern(regexp = "^\\S{5,16}$") String password) {

        User loginUser = userService.findByUserName(username);
        if (loginUser == null) {
            return Result.error("用户名不存在");
        }

        // 2. 直接比对明文密码
        // if (passwordEncoder.matches(password, loginUser.getPassword())) {
        if (password.equals(loginUser.getPassword())) {
            Map<String, Object> claims = new HashMap<>();
            claims.put("id", loginUser.getId());
            claims.put("username", loginUser.getUsername());
            String token = JwtUtil.genToken(claims);
            return Result.success(token);
        }
        return Result.error("密码错误");
    }
}