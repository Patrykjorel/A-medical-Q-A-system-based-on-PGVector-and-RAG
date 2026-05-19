// 文件路径: org/demo/service/UserService.java
package org.demo.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import org.demo.entity.User;
import org.demo.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class UserService {

    @Autowired
    private UserMapper userMapper;


    public User findByUserName(String username) {
        QueryWrapper<User> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("username", username);
        return userMapper.selectOne(queryWrapper);
    }

    public void register(String username, String password) {
        // 2. 直接存储明文密码
        // String encodedPassword = passwordEncoder.encode(password);
        User user = new User();
        user.setUsername(username);
        user.setPassword(password); // 直接使用原始密码
        user.setRole("USER");
        user.setNickname("用户" + System.currentTimeMillis() % 10000);
        userMapper.insert(user);
    }
}