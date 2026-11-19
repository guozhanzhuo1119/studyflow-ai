package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.studyflow.dto.ChatDtos;
import com.studyflow.entity.ChatMessage;
import com.studyflow.entity.ChatSession;
import com.studyflow.mapper.ChatMessageMapper;
import com.studyflow.mapper.ChatSessionMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class ChatPersistenceService {

    private final ChatSessionMapper chatSessionMapper;
    private final ChatMessageMapper chatMessageMapper;

    public ChatPersistenceService(ChatSessionMapper chatSessionMapper,
                                  ChatMessageMapper chatMessageMapper) {
        this.chatSessionMapper = chatSessionMapper;
        this.chatMessageMapper = chatMessageMapper;
    }

    public List<ChatDtos.ChatMessageView> history(String sessionId, int limit) {
        List<ChatMessage> rows = chatMessageMapper.selectList(
                new LambdaQueryWrapper<ChatMessage>()
                        .eq(ChatMessage::getSessionId, sessionId)
                        .orderByDesc(ChatMessage::getId)
                        .last("LIMIT " + limit));
        List<ChatDtos.ChatMessageView> history = new ArrayList<>(rows.size());
        for (int index = rows.size() - 1; index >= 0; index--) {
            ChatMessage row = rows.get(index);
            history.add(new ChatDtos.ChatMessageView(row.getRole(), row.getContent()));
        }
        return history;
    }

    @Transactional
    public void saveExchange(ChatSession session,
                             boolean newSession,
                             String userMessage,
                             String reply,
                             LocalDateTime now) {
        if (newSession) {
            chatSessionMapper.insert(session);
        } else {
            chatSessionMapper.update(null, new LambdaUpdateWrapper<ChatSession>()
                    .eq(ChatSession::getId, session.getId())
                    .set(ChatSession::getUpdatedAt, now));
        }

        ChatMessage user = new ChatMessage();
        user.setSessionId(session.getId());
        user.setRole("user");
        user.setContent(userMessage);
        user.setCreatedAt(now);
        chatMessageMapper.insert(user);

        ChatMessage assistant = new ChatMessage();
        assistant.setSessionId(session.getId());
        assistant.setRole("assistant");
        assistant.setContent(reply);
        assistant.setCreatedAt(now);
        chatMessageMapper.insert(assistant);
    }

    public List<ChatDtos.ChatMessageView> messages(String sessionId) {
        List<ChatMessage> rows = chatMessageMapper.selectList(
                new LambdaQueryWrapper<ChatMessage>()
                        .eq(ChatMessage::getSessionId, sessionId)
                        .orderByAsc(ChatMessage::getId));
        List<ChatDtos.ChatMessageView> views = new ArrayList<>(rows.size());
        for (ChatMessage row : rows) {
            views.add(new ChatDtos.ChatMessageView(row.getRole(), row.getContent()));
        }
        return views;
    }
}
