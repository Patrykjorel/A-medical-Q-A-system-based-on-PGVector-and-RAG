package org.demo.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("user")
public class User {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String username;
    @JsonIgnore // 避免密码在接口返回时被序列化
    private String password;
    private String nickname;
    private String role; // 'SUPER_ADMIN', 'USER'
    private LocalDateTime createdTime;
    // 注意：你的 user 表没有 status, userPic, email, updatedTime, 如果需要请加上
}