package com.studyflow.error;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * 错因枚举、决策树、标签建议与预置映射。
 * 全部照搬 代码/app/models/error.py 与 代码/app/services/error.py，纯 Java 规则，不调 AI。
 */
public final class ErrorCatalog {

    private ErrorCatalog() {
    }

    public record ErrorTypeMeta(
            String code,
            String name,
            int priority,
            String signal,
            String remedy
    ) {
    }

    public record DecisionStep(
            int step,
            String question,
            String resultIfMatch,
            boolean matchAnswer,
            Integer nextStep
    ) {
    }

    public record ErrorTagView(String code, String name, String attachTo) {
    }

    public static final String TAG_SYNTAX = "SYNTAX";
    public static final String REMEDY_PENDING = "待补";
    public static final String REMEDY_DONE = "已补";

    public static final List<String> REMEDY_STATUSES = List.of(REMEDY_PENDING, REMEDY_DONE);

    public static final LinkedHashMap<String, ErrorTypeMeta> ERROR_TYPES = new LinkedHashMap<>();

    static {
        ERROR_TYPES.put("READ", new ErrorTypeMeta("READ", "读题错", 1,
                "看题解后第一反应是「原来问的是这个」",
                "练审题：圈输入范围、输出要求、特殊条件"));
        ERROR_TYPES.put("IDENTIFY", new ErrorTypeMeta("IDENTIFY", "识别错", 2,
                "看题解前完全没方向，看后才知道「原来是这个套路」",
                "补「题面信号 → 模板」对照表，回看母题触发条件"));
        ERROR_TYPES.put("DECOMPOSE", new ErrorTypeMeta("DECOMPOSE", "拆解错", 3,
                "方向对了，但卡在「具体怎么改」",
                "做母题-变体差异对照，强制写一句话拆解"));
        ERROR_TYPES.put("OPERATE", new ErrorTypeMeta("OPERATE", "操作错", 4,
                "看题解发现「我思路没错，就是写错了」",
                "默写原子操作；单独记语言坑"));
        ERROR_TYPES.put("BOUNDARY", new ErrorTypeMeta("BOUNDARY", "边界错", 5,
                "样例过了，提交挂在小数据或特例上",
                "列边界清单，每道题写完强制过一遍"));
        ERROR_TYPES.put("EFFICIENCY", new ErrorTypeMeta("EFFICIENCY", "效率错", 6,
                "答案对但超时/超内存",
                "补复杂度分析，记「这题该用什么复杂度」"));
    }

    public static final List<DecisionStep> DECISION_TREE = List.of(
            new DecisionStep(1, "读完题，你知道要输出什么吗？", "READ", false, 2),
            new DecisionStep(2, "你知道该用什么方法/母题吗？", "IDENTIFY", false, 3),
            new DecisionStep(3, "你知道方法，但不知道怎么落到代码/具体改哪？", "DECOMPOSE", true, 4),
            new DecisionStep(4, "你知道怎么写，但写出来是错的？", "OPERATE", true, 5),
            new DecisionStep(5, "写对了，但漏了某种情况（空/单节点/头节点/进位等）？", "BOUNDARY", true, 6),
            new DecisionStep(6, "都对，但超时/超空间？", "EFFICIENCY", true, null)
    );

    public static final List<String> SYNTAX_KEYWORDS = List.of(
            "->", "nullptr", "size_t", "segfault", "空指针", "越界", "未初始化");

    public static final Map<String, Map<String, String>> TOPIC_TEMPLATES;

    public static final Map<String, List<String>> COMMON_BOUNDARY_CHECKLIST;

    static {
        Map<String, String> linkedList = new LinkedHashMap<>();
        linkedList.put("LC-206", "三指针反转：prev/curr/nextTemp，先存后改");
        linkedList.put("LC-141", "快慢指针：循环条件 fast && fast->next");
        linkedList.put("LC-21", "dummy + tail 合并：退出后整段挂剩余");
        linkedList.put("LC-160", "双指针换路：走完自己换到对方链表");
        linkedList.put("dummyDelete", "可能删头节点：dummy.next = head + prev 前驱删除");

        Map<String, Map<String, String>> templates = new LinkedHashMap<>();
        templates.put("链表", linkedList);
        TOPIC_TEMPLATES = templates;

        Map<String, List<String>> checklists = new LinkedHashMap<>();
        checklists.put("链表", List.of(
                "空链表", "单节点", "删头节点", "找中点后是否断开", "循环条件是否防空指针"));
        COMMON_BOUNDARY_CHECKLIST = checklists;
    }

    public static List<ErrorTypeMeta> errorTypesForApi() {
        return new ArrayList<>(ERROR_TYPES.values());
    }

    public static ErrorTagView syntaxTag() {
        return new ErrorTagView(TAG_SYNTAX, "语法/语言坑", "OPERATE");
    }

    public static boolean isValidErrorType(String code) {
        return code != null && ERROR_TYPES.containsKey(code);
    }

    public static boolean isValidRemedyStatus(String status) {
        return REMEDY_STATUSES.contains(status);
    }

    public static String errorTypeName(String code) {
        ErrorTypeMeta meta = code == null ? null : ERROR_TYPES.get(code);
        return meta == null ? code : meta.name();
    }

    public static String specificBehaviorFallback(String errorType) {
        ErrorTypeMeta meta = ERROR_TYPES.get(errorType);
        return meta == null ? errorType : meta.name();
    }

    public static boolean suggestSyntaxTag(String specificBehavior) {
        if (specificBehavior == null || specificBehavior.isEmpty()) {
            return false;
        }
        String lower = specificBehavior.toLowerCase(Locale.ROOT);
        return SYNTAX_KEYWORDS.stream().anyMatch(kw -> lower.contains(kw.toLowerCase(Locale.ROOT)));
    }

    /**
     * 按回答推导错因：走到第一个命中即停；回答不够时用当前步结论兜底。
     */
    public static String applyDecisionTree(List<Boolean> answers) {
        int index = 0;
        for (DecisionStep step : DECISION_TREE) {
            if (index >= answers.size()) {
                return step.resultIfMatch();
            }
            if (Boolean.valueOf(step.matchAnswer()).equals(answers.get(index))) {
                return step.resultIfMatch();
            }
            index += 1;
        }
        return "EFFICIENCY";
    }

    public static Map<String, Object> presets(String topic) {
        Map<String, Object> result = new LinkedHashMap<>();
        if (topic != null && !topic.isBlank()) {
            Map<String, Map<String, String>> templates = new LinkedHashMap<>();
            templates.put(topic, TOPIC_TEMPLATES.getOrDefault(topic, Map.of()));
            Map<String, List<String>> checklists = new LinkedHashMap<>();
            checklists.put(topic, COMMON_BOUNDARY_CHECKLIST.getOrDefault(topic, List.of()));
            result.put("topic_templates", templates);
            result.put("common_boundary_checklist", checklists);
        } else {
            result.put("topic_templates", TOPIC_TEMPLATES);
            result.put("common_boundary_checklist", COMMON_BOUNDARY_CHECKLIST);
        }
        return result;
    }
}
