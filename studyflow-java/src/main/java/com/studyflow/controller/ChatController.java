package com.studyflow.controller;

import com.studyflow.dto.ChatDtos;
import com.studyflow.service.ChatService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping
    public ChatDtos.ChatResponse chat(@Valid @RequestBody ChatDtos.ChatRequest request) {
        return chatService.chat(request);
    }

    @GetMapping("/sessions")
    public ChatDtos.ChatSessionsResponse sessions() {
        return chatService.sessions();
    }

    @GetMapping("/sessions/{sessionId}/messages")
    public ChatDtos.ChatMessagesResponse messages(@PathVariable String sessionId) {
        return chatService.messages(sessionId);
    }

    @DeleteMapping("/sessions/{sessionId}")
    public Map<String, Object> deleteSession(@PathVariable String sessionId) {
        return chatService.deleteSession(sessionId);
    }
}
