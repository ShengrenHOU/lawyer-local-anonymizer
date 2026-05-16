from legal_anonymizer.risk_scanner import build_risk_report, scan_anonymized_text


def test_second_pass_flags_chinese_company_and_address_residuals():
    text = "请审阅某某投资中心与上海测试科技有限公司，地址为北京市朝阳区测试路100号。"

    findings = scan_anonymized_text(text)
    categories = {finding.category for finding in findings}

    assert "COMPANY" in categories
    assert "ADDRESS" in categories


def test_second_pass_flags_chinese_party_name_residuals():
    text = "甲方：张三\n法定代表人：李四"

    findings = scan_anonymized_text(text)

    assert any(finding.category == "PERSON" for finding in findings)


def test_risk_report_does_not_echo_sensitive_values():
    text = "甲方：张三"
    findings = scan_anonymized_text(text)

    report = build_risk_report(findings)

    assert "张三" not in report
    assert "PERSON" in report
