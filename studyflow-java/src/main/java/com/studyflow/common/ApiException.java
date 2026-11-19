package com.studyflow.common;

/**
 * 业务异常：由全局异常处理器转成 {"detail": "..."}。
 * 状态码与旧版 FastAPI 的 HTTPException 保持一致。
 */
public class ApiException extends RuntimeException {

    private final int status;

    public ApiException(int status, String message) {
        super(message);
        this.status = status;
    }

    public int getStatus() {
        return status;
    }
}
