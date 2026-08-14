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
                            "- Months: 1월→Jan/一月/1月, 2월→Feb/二月/2月, 3월→Mar/三月/3月, 4월→Apr/四月/4月, "
                            "5월→May/五月/5月, 6월→Jun/六月/6月, 7월→Jul/七月/7月, 8월→Aug/八月/8月, "
                            "9월→Sep/九月/9月, 10월→Oct/十月/10月, 11월→Nov/十一月/11月, 12월→Dec/十二月/12月\n"
                            "- Quarters: 1분기→Q1/第一季度/第1四半期, 2분기→Q2/第二季度/第2四半期, "
                            "3분기→Q3/第三季度/第3四半期, 4분기→Q4/第四季度/第4四半期\n"
                            "- Year+Month: '2024년 7월'→'July 2024'/'2024年7月'/'2024年7月'\n\n"

                            "## Quality & Manufacturing Terms\n"
                            "- 불량률→Defect Rate/不良率/不良率\n"
                            "- 수율→Yield Rate/良品率/歩留まり\n"
                            "- 개선대책→Corrective Action/改善对策/是正処置\n"
                            "- 품질보증→Quality Assurance(QA)/品质保证/品質保証\n"
                            "- 품질관리→Quality Control(QC)/品质管理/品質管理\n"
                            "- 원인분석→Root Cause Analysis/原因分析/原因分析\n"
                            "- 재발방지→Recurrence Prevention/防止再发/再発防止\n"
                            "- 공정→Process/工序/工程\n"
                            "- 가동률→Operation Rate/开动率/稼働率\n"
                            "- 생산량→Production Volume/产量/生産量\n"
                            "- 납기→Delivery Date/交期/納期\n"
                            "- 수율개선→Yield Improvement/良品率提升/歩留まり改善\n\n"

                            "## Status & Progress\n"
                            "- 진행중→In Progress/进行中/進行中\n"
                            "- 완료→Completed/完成/完了\n"
                            "- 검토중→Under Review/审核中/検討中\n"
                            "- 보류→On Hold/暂停/保留\n"
                            "- 미완료→Incomplete/未完成/未完了\n"
                            "- 예정→Planned/计划/予定\n"
                            "- 지연→Delayed/延迟/遅延\n\n"

                            "## Business & Organization\n"
                            "- 담당자→Person in Charge/负责人/担当者\n"
                            "- 협력사→Supplier/供应商/サプライヤー\n"
                            "- 발주→Purchase Order(PO)/订单/発注\n"
                            "- 총결보고→Summary Report/总结报告/総括報告\n"
                            "- 현황→Status/现状/現状\n"
                            "- 조치사항→Action Items/措施事项/対応事項\n"
                            "- 기한→Deadline/截止日期/期限\n"
                            "- 목표→Target/目标/目標\n"
                            "- 실적→Actual Results/实绩/実績\n"
                            "- 달성률→Achievement Rate/达成率/達成率\n\n"

                            "## General Rules\n"
                            "- Preserve as-is: numbers, model codes, part numbers, abbreviations (PPM, SQE, Cpk, QA, QC, PO, etc.)\n"
                            "- Keep symbols unchanged: %, /, -, _, ·, →, ±\n"
                            "- For Japanese output: use formal business style (です/ます調 where appropriate)\n"
                            "- For Chinese output: use Simplified Chinese standard business terminology\n"
                            "- Short fragments (single words/numbers): infer from semiconductor/manufacturing business context\n"
                            "- Never add explanations, parentheses, or notes to the translation"
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
