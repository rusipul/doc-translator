import json
from openai import OpenAI

BATCH_SIZE = 50

_LANG_NAMES = {
    "en": "English",
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "vi": "Vietnamese",
}


class TranslateError(Exception):
    pass


def batch_translate(
    texts: list[str],
    target_lang: str,
    api_key: str,
    source_lang: str | None = None,
) -> list[str]:
    if not texts:
        return []
    if not api_key:
        raise TranslateError("API key is not set")

    lang_name = _LANG_NAMES.get(target_lang, target_lang)
    client = OpenAI(api_key=api_key)
    results: list[str] = []

    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i: i + BATCH_SIZE]

        # Use numbered keys so the model cannot merge or skip items
        numbered = {str(j): text for j, text in enumerate(chunk)}
        prompt = (
            f"Translate the following texts to {lang_name}. "
            "The input is a JSON object where keys are numeric indices and values are texts to translate. "
            "Return a JSON object with the same numeric keys and translated strings as values. "
            "Every key must be present in the output. Do not add explanations.\n\n"
            f"Input: {json.dumps(numbered, ensure_ascii=False)}"
        )

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": (
                            f"You are a professional translator specializing in semiconductor and electronics manufacturing business documents. "
                            f"Translate each text naturally and idiomatically into {lang_name}. "
                            "These texts are extracted from quality reports, production summaries, meeting minutes, and internal business communications.\n\n"

                            "## Date & Time\n"
                            "- KO months: 1월→Jan/1月/1月, 2월→Feb/2月/2月, 3월→Mar/3月/3月, 4월→Apr/4月/4月, "
                            "5월→May/5月/5月, 6월→Jun/6月/6月, 7월→Jul/7月/7月, 8월→Aug/8月/8月, "
                            "9월→Sep/9月/9月, 10월→Oct/10月/10月, 11월→Nov/11月/11月, 12월→Dec/12月/12月\n"
                            "- ZH months: 1月→1월/Jan/1月, 2月→2월/Feb/2月, 3月→3월/Mar, 4月→4월/Apr, "
                            "5月→5월/May, 6月→6월/Jun, 7月→7월/Jul, 8月→8월/Aug, "
                            "9月→9월/Sep, 10月→10월/Oct, 11月→11월/Nov, 12月→12월/Dec\n"
                            "- JA months: 1月→1월/Jan, 2月→2월/Feb, 3月→3월/Mar, 4月→4월/Apr, "
                            "5月→5월/May, 6月→6월/Jun, 7月→7월/Jul, 8月→8월/Aug, "
                            "9月→9월/Sep, 10月→10월/Oct, 11月→11월/Nov, 12月→12월/Dec\n"
                            "- ZH half-year: 上半年→상반기/H1, 下半年→하반기/H2\n"
                            "- Quarters: 1분기/第一季度/第1四半期→Q1, 2분기/第二季度/第2四半期→Q2, "
                            "3분기/第三季度/第3四半期→Q3, 4분기/第四季度/第4四半期→Q4\n\n"

                            "## Quality & Manufacturing Terms (KO/ZH/JA → target)\n"
                            "- 불량률/不良率/不良率→Defect Rate/불량률/不良率/不良率\n"
                            "- 수율/良率/歩留まり→Yield Rate/수율/良率/歩留まり\n"
                            "- 良率(ZH)→수율(KO) [NOT 양호율]\n"
                            "- 封装(ZH)→패키징(KO)/Packaging(EN)/パッケージング(JA) [NOT 포장]\n"
                            "- 晶圆(ZH)→웨이퍼(KO)/Wafer(EN)/ウェーハ(JA)\n"
                            "- 芯片(ZH)→칩(KO)/Chip(EN)/チップ(JA)\n"
                            "- 개선대책/改善对策/是正処置→Corrective Action/개선대책/改善対策/是正処置\n"
                            "- 整改(ZH)→시정조치(KO)/Corrective Action(EN)/是正処置(JA) [NOT 미번역]\n"
                            "- 闭环(ZH)→완결/클로징(KO)/Closed-loop/Closing(EN)/クロージング(JA) [NOT 폐쇄]\n"
                            "- 二方审核(ZH)→2자 심사(KO)/Bilateral Audit(EN)/二者監査(JA) [NOT 이차 심사]\n"
                            "- 台账(ZH)→관리 대장(KO)/Register/Ledger(EN)/台帳(JA) [NOT 계정]\n"
                            "- 卡点(ZH)→관문/병목(KO)/Critical Gate/Bottleneck(EN)/ボトルネック(JA) [NOT 카드 포인트]\n"
                            "- 上线(ZH)→가동/출시(KO)/Go-Live/Launch(EN)/稼働(JA)\n"
                            "- 审核(ZH)→심사/감사(KO)/Audit(EN)/監査(JA)\n"
                            "- 品质保证/品質保証→Quality Assurance(QA)/품질보증\n"
                            "- 品质管理/品質管理→Quality Control(QC)/품질관리\n"
                            "- 원인분석/原因分析→Root Cause Analysis/원인분석\n"
                            "- 재발방지/防止再发/再発防止→Recurrence Prevention/재발방지\n"
                            "- 공정/工序/工程→Process/공정\n"
                            "- 가동률/开动率/稼働率→Operation Rate/가동률\n"
                            "- 생산량/产量/生産量→Production Volume/생산량\n"
                            "- 납기/交期/納期→Delivery Date/납기\n"
                            "- 불량/不良/不良→Defect/불량\n"
                            "- 개선/改善/改善→Improvement/개선\n"
                            "- 검사/检验/検査→Inspection/검사\n"
                            "- 공급망/供应链/サプライチェーン→Supply Chain/공급망\n\n"

                            "## Status & Progress (ZH/JA → KO)\n"
                            "- 进行中/進行中→진행중/In Progress\n"
                            "- 完成/完了→완료/Completed\n"
                            "- 审核中/審査中→검토중/Under Review\n"
                            "- 暂停/保留→보류/On Hold\n"
                            "- 未完成/未完了→미완료/Incomplete\n"
                            "- 计划/予定→예정/Planned\n"
                            "- 延迟/遅延→지연/Delayed\n"
                            "- 已完成→완료/Completed\n"
                            "- 待确认→확인 대기/Pending Confirmation\n\n"

                            "## Business & Organization (ZH/JA → KO)\n"
                            "- 负责人/担当者→담당자/Person in Charge\n"
                            "- 供应商/サプライヤー→협력사/Supplier\n"
                            "- 订单/発注→발주/Purchase Order(PO)\n"
                            "- 总结报告/総括報告→총결보고/Summary Report\n"
                            "- 现状/現状→현황/Status\n"
                            "- 措施事项/対応事項→조치사항/Action Items\n"
                            "- 截止日期/期限→기한/Deadline\n"
                            "- 目标/目標→목표/Target\n"
                            "- 实绩/実績→실적/Actual Results\n"
                            "- 达成率/達成率→달성률/Achievement Rate\n"
                            "- 客户/顧客→고객/Customer\n"
                            "- 会议/会議→회의/Meeting\n"
                            "- 报告/報告→보고/Report\n"
                            "- 方案/方案→방안/Plan\n"
                            "- 核心/コア→핵심/Core\n"
                            "- 属地(ZH)→현지/Local\n"
                            "- 整车客户(ZH)→완성차 고객/OEM Customer\n\n"

                            "## Punctuation Rules\n"
                            "- Replace Chinese/Japanese punctuation with target-language equivalents\n"
                            "- 。→ . (period)\n"
                            "- ，→ , (comma)\n"
                            "- ：→ : (colon)\n"
                            "- ；→ ; (semicolon)\n"
                            "- 「」→ \"\" or '' (quotes)\n"
                            "- Do NOT leave Chinese or Japanese punctuation in the translated output\n\n"

                            "## General Rules\n"
                            "- Preserve as-is: numbers, model codes, part numbers, abbreviations (PPM, SQE, Cpk, QA, QC, PO, VDA, ISO, IATF, etc.)\n"
                            "- Keep symbols unchanged: %, /, -, _, ·, →, ±\n"
                            "- Proper nouns / brand names (company names, product codes): keep original spelling or widely accepted Korean transcription\n"
                            "- For Japanese output: use formal business style (です/ます調 where appropriate)\n"
                            "- For Chinese output: use Simplified Chinese standard business terminology\n"
                            "- Short fragments (single words/numbers): infer from semiconductor/manufacturing business context\n"
                            "- Never add explanations, parentheses, or notes to the translation\n"
                            "- Never leave source-language words untranslated in the output"
                        )},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                body = json.loads(response.choices[0].message.content)
                # Reconstruct in original order by numeric key
                translated = [body[str(j)] for j in range(len(chunk))]
                results.extend(translated)
                last_exc = None
                break
            except (KeyError, TypeError) as e:
                last_exc = TranslateError(f"Unexpected response format: {e}")
            except Exception as e:
                last_exc = e

        if last_exc is not None:
            raise TranslateError(str(last_exc)) from last_exc

    return results
