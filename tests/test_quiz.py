"""Tests for quiz generation, validation and grading.

Grading is pure Python, so it is tested thoroughly. Gemma is never called here:
the tests feed the parser the kind of text a small model actually produces.
"""

from app import quiz


class TestJsonExtraction:
    def test_plain_json_array(self):
        raw = '[{"question": "Q1", "options": ["a", "b", "c", "d"], "correct_index": 0}]'
        payload = quiz._extract_json_array(raw)
        assert isinstance(payload, list) and payload[0]["question"] == "Q1"

    def test_json_inside_code_fence(self):
        raw = '```json\n[{"question": "Q1"}]\n```'
        assert quiz._extract_json_array(raw) == [{"question": "Q1"}]

    def test_json_wrapped_in_prose(self):
        raw = 'Sure! Here it is:\n[{"question": "Q1"}]\nHope this helps!'
        assert quiz._extract_json_array(raw) == [{"question": "Q1"}]

    def test_json_with_trailing_comma_breaks_parse(self):
        # Malformed output must return None, never raise or half-parse.
        assert quiz._extract_json_array('[{"question": "Q1",}]') is None

    def test_no_json_returns_none(self):
        assert quiz._extract_json_array("I cannot help with that.") is None
        assert quiz._extract_json_array("") is None


class TestQuestionValidation:
    def _entry(self, **overrides):
        entry = {
            "question": "Which normal form removes partial dependency?",
            "options": ["1NF", "2NF", "3NF", "BCNF"],
            "correct_index": 1,
            "explanation": "2NF removes partial dependencies.",
        }
        entry.update(overrides)
        return entry

    def test_valid_entry_becomes_question(self):
        questions = quiz._questions_from_json([self._entry()], 5)
        assert len(questions) == 1
        question = questions[0]
        assert question.correct_index == 1
        assert question.correct_letter == "B"
        assert question.options[0] == "A. 1NF"
        assert "partial" in question.explanation

    def test_lettered_options_are_relabelled(self):
        entry = self._entry(options=["A. 1NF", "B. 2NF", "C. 3NF", "D. BCNF"])
        question = quiz._questions_from_json([entry], 1)[0]
        assert question.options == ["A. 1NF", "B. 2NF", "C. 3NF", "D. BCNF"]

    def test_correct_answer_letter_is_accepted(self):
        entry = self._entry(correct_index=None)
        entry.pop("correct_index")
        entry["correct_answer"] = "C"
        assert quiz._questions_from_json([entry], 1)[0].correct_letter == "C"

    def test_invalid_entries_are_dropped(self):
        entries = [
            self._entry(question=""),  # no question text
            self._entry(options=["a", "a", "c", "d"]),  # duplicate options
            self._entry(options=["a", "b"]),  # wrong number of options
            self._entry(correct_index=9),  # index out of range
            {"question": "no options key"},
        ]
        assert quiz._questions_from_json(entries, 5) == []

    def test_missing_explanation_gets_a_default(self):
        entry = self._entry()
        entry.pop("explanation")
        question = quiz._questions_from_json([entry], 1)[0]
        assert question.explanation

    def test_respects_requested_count(self):
        entries = [self._entry(question=f"Question {i}") for i in range(10)]
        assert len(quiz._questions_from_json(entries, 3)) == 3


class TestTextFallbackParser:
    RAW = """QUESTION: Which normal form removes partial dependency?
A. 1NF
B. 2NF
C. 3NF
D. BCNF
ANSWER: B
WHY: 2NF removes partial dependencies.

QUESTION: What does atomicity mean?
A. Fast writes
B. All operations or none
C. No locking
D. Auto commit
ANSWER: B
WHY: Atomicity means every operation completes or none do.
"""

    def test_parses_both_questions(self):
        questions = quiz._questions_from_text(self.RAW, 5)
        assert len(questions) == 2
        assert questions[0].correct_letter == "B"
        assert questions[1].correct_letter == "B"

    def test_keeps_options_and_explanations(self):
        question = quiz._questions_from_text(self.RAW, 5)[0]
        assert question.options == ["A. 1NF", "B. 2NF", "C. 3NF", "D. BCNF"]
        assert "partial" in question.explanation

    def test_garbage_returns_no_questions(self):
        assert quiz._questions_from_text("I'm sorry, I can't do that.", 5) == []


class TestGrading:
    def _questions(self):
        payload = [
            {
                "question": f"Question {i}",
                "options": ["A. one", "B. two", "C. three", "D. four"],
                "correct_index": i % 4,
                "explanation": "because",
            }
            for i in range(4)
        ]
        return quiz._questions_from_json(payload, 4)

    def test_all_correct(self):
        result = quiz.score_quiz(self._questions(), [0, 1, 2, 3])
        assert result["score"] == 4
        assert result["total"] == 4
        assert result["percent"] == 100
        assert all(result["detail"])

    def test_partial_and_skipped(self):
        result = quiz.score_quiz(self._questions(), [0, 0, None, 3])
        assert result["score"] == 2
        assert result["percent"] == 50
        assert result["detail"] == [True, False, False, True]

    def test_empty_answers_score_zero(self):
        result = quiz.score_quiz(self._questions(), [None] * 4)
        assert result["score"] == 0
        assert result["percent"] == 0

    def test_missing_answers_are_treated_as_skipped(self):
        result = quiz.score_quiz(self._questions(), [0])
        assert result["score"] == 1
        assert result["total"] == 4

    def test_result_message_mentions_the_score(self):
        message = quiz.result_message(quiz.score_quiz(self._questions(), [0, 1, 2, 3]))
        assert "4 / 4" in message


class TestQuizGuards:
    def test_empty_topic_is_rejected(self):
        try:
            quiz.build_quiz("   ", count=3)
        except quiz.QuizError as exc:
            assert "topic" in str(exc).lower()
        else:  # pragma: no cover
            raise AssertionError("empty topic should be rejected")

    def test_explanation_defaults_when_missing_in_text_format(self):
        raw = "QUESTION: Q?\nA. a\nB. b\nC. c\nD. d\nANSWER: A"
        question = quiz._questions_from_text(raw, 1)[0]
        assert question.explanation
