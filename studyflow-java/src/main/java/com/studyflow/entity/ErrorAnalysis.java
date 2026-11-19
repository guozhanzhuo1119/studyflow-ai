package com.studyflow.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import java.time.LocalDateTime;

@TableName("error_analyses")
public class ErrorAnalysis {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    private String problemId;
    private String problemTitle;
    private String topic;
    private String motherProblem;
    private String errorType;
    private String tag;
    private String specificBehavior;
    private String firstBreakPoint;
    private String decompositionSentence;
    private String remedyStatus;
    private String remedyAction;
    private String userNote;
    private Boolean reviewed;
    private LocalDateTime createdAt;
    private Integer identifyLatencySec;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getProblemId() {
        return problemId;
    }

    public void setProblemId(String problemId) {
        this.problemId = problemId;
    }

    public String getProblemTitle() {
        return problemTitle;
    }

    public void setProblemTitle(String problemTitle) {
        this.problemTitle = problemTitle;
    }

    public String getTopic() {
        return topic;
    }

    public void setTopic(String topic) {
        this.topic = topic;
    }

    public String getMotherProblem() {
        return motherProblem;
    }

    public void setMotherProblem(String motherProblem) {
        this.motherProblem = motherProblem;
    }

    public String getErrorType() {
        return errorType;
    }

    public void setErrorType(String errorType) {
        this.errorType = errorType;
    }

    public String getTag() {
        return tag;
    }

    public void setTag(String tag) {
        this.tag = tag;
    }

    public String getSpecificBehavior() {
        return specificBehavior;
    }

    public void setSpecificBehavior(String specificBehavior) {
        this.specificBehavior = specificBehavior;
    }

    public String getFirstBreakPoint() {
        return firstBreakPoint;
    }

    public void setFirstBreakPoint(String firstBreakPoint) {
        this.firstBreakPoint = firstBreakPoint;
    }

    public String getDecompositionSentence() {
        return decompositionSentence;
    }

    public void setDecompositionSentence(String decompositionSentence) {
        this.decompositionSentence = decompositionSentence;
    }

    public String getRemedyStatus() {
        return remedyStatus;
    }

    public void setRemedyStatus(String remedyStatus) {
        this.remedyStatus = remedyStatus;
    }

    public String getRemedyAction() {
        return remedyAction;
    }

    public void setRemedyAction(String remedyAction) {
        this.remedyAction = remedyAction;
    }

    public String getUserNote() {
        return userNote;
    }

    public void setUserNote(String userNote) {
        this.userNote = userNote;
    }

    public Boolean getReviewed() {
        return reviewed;
    }

    public void setReviewed(Boolean reviewed) {
        this.reviewed = reviewed;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public Integer getIdentifyLatencySec() {
        return identifyLatencySec;
    }

    public void setIdentifyLatencySec(Integer identifyLatencySec) {
        this.identifyLatencySec = identifyLatencySec;
    }
}
