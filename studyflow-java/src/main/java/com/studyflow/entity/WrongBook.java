package com.studyflow.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import java.time.LocalDateTime;

@TableName("wrong_book")
public class WrongBook {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    private String targetType;
    private String targetId;
    private String title;
    private Integer wrongCount;
    private Boolean mastered;
    private LocalDateTime lastWrongAt;
    private LocalDateTime masteredAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTargetType() {
        return targetType;
    }

    public void setTargetType(String targetType) {
        this.targetType = targetType;
    }

    public String getTargetId() {
        return targetId;
    }

    public void setTargetId(String targetId) {
        this.targetId = targetId;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public Integer getWrongCount() {
        return wrongCount;
    }

    public void setWrongCount(Integer wrongCount) {
        this.wrongCount = wrongCount;
    }

    public Boolean getMastered() {
        return mastered;
    }

    public void setMastered(Boolean mastered) {
        this.mastered = mastered;
    }

    public LocalDateTime getLastWrongAt() {
        return lastWrongAt;
    }

    public void setLastWrongAt(LocalDateTime lastWrongAt) {
        this.lastWrongAt = lastWrongAt;
    }

    public LocalDateTime getMasteredAt() {
        return masteredAt;
    }

    public void setMasteredAt(LocalDateTime masteredAt) {
        this.masteredAt = masteredAt;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
}
