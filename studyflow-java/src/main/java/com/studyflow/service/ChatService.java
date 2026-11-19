package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.studyflow.ai.AiClient;
import com.studyflow.ai.AiDtos;
import com.studyflow.common.ApiException;
import com.studyflow.dto.ChatDtos;
import com.studyflow.entity.ChatMessage;
import com.studyflow.entity.ChatSession;
import com.studyflow.entity.Problem;
import com.studyflow.entity.Subject;
import com.studyflow.mapper.ChatMessageMapper;
import com.studyflow.mapper.ChatSessionMapper;
import com.studyflow.mapper.ProblemMapper;
import com.studyflow.mapper.SubjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class ChatService {

    private static final Logger log = LoggerFactory.getLogger(ChatService.class);
    private static final int HISTORY_LIMIT = 20; // 10 轮（user + assistant）

    private final AiClient aiClient;
    private final ChatSessionMapper chatSessionMapper;
    private final ChatMessageMapper chatMessageMapper;
    private final ProblemMapper problemMapper;
    private final SubjectMapper subjectMapper;
    private final ChatPersistenceService chatPersistenceService;
    private final ObjectMapper objectMapper;

    public ChatService(AiClient aiClient,
                       ChatSessionMapper chatSessionMapper,
                       ChatMessageMapper chatMessageMapper,
                       ProblemMapper problemMapper,
                       SubjectMapper subjectMapper,
                       ChatPersistenceService chatPersistenceService,
                       ObjectMapper objectMapper) {
        this.aiClient = aiClient;
        this.chatSessionMapper = chatSessionMapper;
        this.chatMessageMapper = chatMessageMapper;
        this.problemMapper = problemMapper;
        this.subjectMapper = subjectMapper;
        this.chatPersistenceService = chatPersistenceService;
        this.objectMapper = objectMapper;
    }

    public ChatDtos.ChatResponse chat(ChatDtos.ChatRequest request) {
        String message = request.message().strip();
        if (message.isEmpty()) {
            throw new ApiException(400, "消息不能为空");
        }

        AiDtos.ChatQuestion question = null;
        if (request.questionId() != null && !request.questionId().isBlank()) {
            Problem problem = problemMapper.selectById(request.questionId());
            if (problem == null) {
                throw new ApiException(404, "题目不存在");
            }
            question = new AiDtos.ChatQuestion(
                    problem.getTitle(),
                    parseOptions(problem.getOptions()),
                    null,
                    problem.getAnswer(),
                    problem.getExplanation());
        }

        String sessionId = request.sessionId();
        if (sessionId == null || sessionId.isBlank()) {
            sessionId = "session-" + shortId();
        } else if (sessionId.length() > 36) {
            throw new ApiException(400, "session_id 长度不能超过 36");
        }

        ChatSession session = chatSessionMapper.selectById(sessionId);
        boolean newSession = session == null;
        LocalDateTime now = LocalDateTime.now();
        if (newSession) {
            session = new ChatSession();
            session.setId(sessionId);
            session.setTitle(truncate(message, 40));
            session.setUserId(null);
            session.setCreatedAt(now);
            session.setUpdatedAt(now);
        }

        List<ChatDtos.ChatMessageView> history = newSession
                ? List.of()
                : chatPersistenceService.history(sessionId, HISTORY_LIMIT);

        List<AiDtos.ChatHistoryItem> aiHistory = new ArrayList<>(history.size());
        for (ChatDtos.ChatMessageView item : history) {
            aiHistory.add(new AiDtos.ChatHistoryItem(item.role(), item.content()));
        }

        String scopedMessage = message;
        if (request.subjectId() != null && !request.subjectId().isBlank()) {
            Subject subject = subjectMapper.selectById(request.subjectId());
            if (subject != null) {
                scopedMessage = "【当前科目：" + subject.getName() + "】\n" + message;
            }
        }

        AiDtos.ChatData data = aiClient.chat(new AiDtos.ChatRequest(
                "xinyuehu",
                question,
                aiHistory,
                scopedMessage));

        String reply = data.reply() == null ? "" : data.reply().strip();
        if (reply.isEmpty()) {
            throw new ApiException(502, "AI 服务没有返回回复");
        }

        chatPersistenceService.saveExchange(session, newSession, message, reply, now);
        log.info("聊天完成：session={}, history_messages={}, reply_chars={}",
                sessionId, aiHistory.size(), reply.length());

        return new ChatDtos.ChatResponse(reply, sessionId);
    }

    public ChatDtos.ChatMessagesResponse messages(String sessionId) {
        if (chatSessionMapper.selectById(sessionId) == null) {
            throw new ApiException(404, "会话不存在");
        }
        return new ChatDtos.ChatMessagesResponse(sessionId, chatPersistenceService.messages(sessionId));
    }

    public ChatDtos.ChatSessionsResponse sessions() {
        List<ChatSession> sessions = chatSessionMapper.selectList(
                new LambdaQueryWrapper<ChatSession>().orderByDesc(ChatSession::getUpdatedAt));
        List<ChatDtos.ChatSessionView> views = new ArrayList<>(sessions.size());
        for (ChatSession session : sessions) {
            Long count = chatMessageMapper.selectCount(
                    new LambdaQueryWrapper<ChatMessage>()
                            .eq(ChatMessage::getSessionId, session.getId()));
            views.add(new ChatDtos.ChatSessionView(
                    session.getId(),
                    session.getTitle(),
                    count == null ? 0L : count,
                    session.getUpdatedAt()));
        }
        return new ChatDtos.ChatSessionsResponse(views);
    }

    @Transactional
    public Map<String, Object> deleteSession(String sessionId) {
        if (chatSessionMapper.selectById(sessionId) == null) {
            throw new ApiException(404, "会话不存在");
        }
        chatMessageMapper.delete(new LambdaQueryWrapper<ChatMessage>()
                .eq(ChatMessage::getSessionId, sessionId));
        chatSessionMapper.deleteById(sessionId);
        return Map.of("message", "会话已删除");
    }

    private List<String> parseOptions(String raw) {
        if (raw == null || raw.isBlank()) {
            return List.of();
        }
        try {
            List<Object> parsed = objectMapper.readValue(raw, new TypeReference<List<Object>>() {
            });
            if (parsed == null) {
                return List.of();
            }
            List<String> options = new ArrayList<>(parsed.size());
            for (Object item : parsed) {
                options.add(item == null ? "" : String.valueOf(item));
            }
            return options;
        } catch (Exception ex) {
            return List.of();
        }
    }

    private static String truncate(String value, int max) {
        if (value == null) {
            return null;
        }
        return value.length() <= max ? value : value.substring(0, max);
    }

    private static String shortId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 8);
    }
}
