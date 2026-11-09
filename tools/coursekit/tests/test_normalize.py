from coursekit.normalize import normalize_text


def test_bold_heading_becomes_canonical():
    out, _ = normalize_text("### **План лекции:**\n")
    assert out == "## План лекции\n"


def test_numbered_heading_without_bold():
    out, _ = normalize_text("### 1. Введение\n")
    assert out == "## 1. Введение\n"


def test_subsection_numbered_keeps_level_three():
    out, _ = normalize_text("### 1.1. Подраздел\n")
    assert out == "### 1.1. Подраздел\n"


def test_h1_with_bold_normalized():
    out, _ = normalize_text("## **1. Введение**\n")
    assert out == "## 1. Введение\n"


def test_hash_inside_fenced_code_is_untouched():
    src = "````markdown\n# Заголовок readme\n````\n"
    out, _ = normalize_text(src)
    assert "# Заголовок readme" in out
    assert out.count("````") == 2


def test_fence_without_language_is_left_bare_and_warned():
    src = "```\nConsole.WriteLine();\n```\n"
    out, warnings = normalize_text(src)
    assert "```\nConsole" in out
    assert any("язык" in w.lower() for w in warnings)


def test_horizontal_rule_removed():
    out, _ = normalize_text("Текст\n\n---\n\nЕщё текст\n")
    assert "---" not in out


def test_normalization_is_idempotent():
    src = "### **1. Введение**\n\nТекст\n\n### **План лекции:**\n"
    once, _ = normalize_text(src)
    twice, _ = normalize_text(once)
    assert once == twice


def test_body_text_not_rewritten():
    src = "Visual Studio больше не используется.\n"
    out, _ = normalize_text(src)
    assert out == src
