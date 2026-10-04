"""Tests for study plan generation: batched enrichment and task creation.

Gemma is never called here. The tests feed the parser the kind of text a small
model actually produces, and check that a partial answer improves the plan
without inventing anything for the days it got wrong.
"""

from datetime import date

from app import database, planner


def source(page: int = 4):
    return planner.Source(
        filename="db.pdf",
        page=page,
        text="Functional dependencies and normal forms.",
        chunk_id="c1",
        score=0.9,
    )


TOPICS = ["Normalisation", "Transactions", "Indexing", "Recovery"]


def topic_for(number: int) -> str:
    """Distinct focus per day, so an off-topic answer is detectable."""
    return TOPICS[(number - 1) % len(TOPICS)] + (f" {number}" if number > len(TOPICS) else "")


def day(number: int, topics=None, generated_bullets=None, **kwargs):
    return planner.StudyDay(
        day_number=number,
        date=date(2026, 10, 4) + planner.timedelta(days=number - 1),
        topics=topics or [topic_for(number)],
        reading="p. 4",
        bullets=generated_bullets
        or [f"Read {number}", f"Summarise {number}", f"Test {number}"],
        sources=[source()],
        **kwargs,
    )


def about(number: int) -> list[str]:
    """Plausible model bullets for a day, naming that day's own focus."""
    topic = topic_for(number)
    return [
        f"Read the {topic} section on page 4",
        f"Cover the main {topic} definitions",
        f"Try five {topic} questions",
    ]


def answer(*days: int) -> str:
    import json

    return json.dumps([{"day": n, "bullets": about(n)} for n in days])


class FakeGenerate:
    """Stands in for `planner.generate`, recording every call."""

    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def __call__(self, prompt, system_prompt=None, model=None, temperature=None, max_tokens=None):
        self.prompts.append((prompt, max_tokens))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def enrich(fake, days=None):
    days = days or [day(1), day(2), day(3)]
    planner.generate = fake
    try:
        notes = planner._enrich_days(days, "DB Systems", date(2026, 10, 9))
    finally:
        planner.generate = FakeGenerate("")
    return notes, days


class TestBatchedEnrichment:
    def test_one_call_covers_every_day(self):
        fake = FakeGenerate(answer(1, 2, 3))
        notes, days = enrich(fake)
        assert len(fake.prompts) == 1, "the whole plan must be one request"
        assert notes == ""
        assert all(d.generated for d in days)
        assert [d.bullets[0] for d in days] == [
            "Read the Normalisation section on page 4",
            "Read the Transactions section on page 4",
            "Read the Indexing section on page 4",
        ]

    def test_bullets_are_taken_from_the_matching_day(self):
        fake = FakeGenerate(answer(2))
        _, days = enrich(fake)
        assert days[1].bullets[0] == "Read the Transactions section on page 4"
        assert days[0].generated is False
        assert days[2].generated is False

    def test_missing_day_keeps_its_computed_bullets(self):
        fake = FakeGenerate(answer(1))
        notes, days = enrich(fake)
        assert days[0].generated is True
        assert days[1].bullets == ["Read 2", "Summarise 2", "Test 2"]
        assert "2 of 3 day(s) fell back" in notes

    def test_bullets_about_another_day_are_rejected(self):
        # The model answered Day 2 with Day 3's subject. That reads as correct on
        # the page, so the day keeps its own checklist instead.
        import json

        fake = FakeGenerate(
            json.dumps([{"day": 2, "bullets": about(3)}])
        )
        notes, days = enrich(fake)
        assert days[1].generated is False
        assert days[1].bullets == ["Read 2", "Summarise 2", "Test 2"]
        assert "wrong topic" in notes

    def test_json_inside_a_code_fence_with_prose(self):
        fake = FakeGenerate("Sure!\n```json\n" + answer(1) + "\n```\nHope that helps.")
        _, days = enrich(fake, [day(1)])
        assert days[0].bullets[0] == "Read the Normalisation section on page 4"

    def test_trailing_commas_are_recovered(self):
        fake = FakeGenerate(answer(1).replace('"Try five Normalisation questions"', '"Try five Normalisation questions",'))
        fake.reply = "[" + fake.reply[1:-1] + ",]"
        _, days = enrich(fake, [day(1)])
        assert days[0].generated is True

    def test_unusable_output_leaves_the_plan_alone(self):
        fake = FakeGenerate("I'm sorry, I cannot help with that.")
        notes, days = enrich(fake)
        assert all(d.generated is False for d in days)
        assert "every day uses the default checklist" in notes

    def test_local_model_unavailable_is_not_an_error(self):
        fake = FakeGenerate(planner.OllamaUnavailableError("Ollama is not running."))
        notes, days = enrich(fake)
        assert notes == ""
        assert all(d.generated is False for d in days)

    def test_consolidation_days_are_left_out_of_the_request(self):
        fake = FakeGenerate("[]")
        days = [
            day(1),
            day(2, topics=["Consolidation and practice"]),
        ]
        notes, _ = enrich(fake, days)
        assert len(fake.prompts) == 1
        assert "Consolidation and practice" not in fake.prompts[0][0]
        assert days[1].generated is False

    def test_days_without_material_are_left_out_of_the_request(self):
        fake = FakeGenerate("[]")
        bare = day(2)
        bare.sources = []
        notes, _ = enrich(fake, [day(1), bare])
        assert '"day": 2' not in fake.prompts[0][0]

    def test_long_plans_get_a_larger_token_budget(self):
        fake = FakeGenerate("[]")
        planner.generate = fake
        try:
            planner._enrich_days([day(n) for n in range(1, 9)], "DB", date(2026, 10, 9))
        finally:
            planner.generate = FakeGenerate("")
        assert fake.prompts[0][1] > 200

    def test_prompt_names_every_day_and_asks_for_json(self):
        fake = FakeGenerate("[]")
        planner.generate = fake
        try:
            planner._enrich_days([day(1), day(2)], "DB Systems", date(2026, 10, 9))
        finally:
            planner.generate = FakeGenerate("")
        prompt = fake.prompts[0][0]
        assert "DB Systems" in prompt
        assert '"day": 1' in prompt and '"day": 2' in prompt
        assert "JSON array" in prompt


class TestPlanTasks:
    def _plan(self):
        return planner.StudyPlanResult(
            exam_name="DB Systems",
            exam_date=date(2026, 10, 9),
            total_days=3,
            hours_per_day=2.0,
            days=[day(1), day(2), day(3)],
        )

    def _plan_tasks(self, exam_name):
        return [
            task
            for task in database.list_tasks()
            if task.title.startswith(planner.TASK_SOURCE_PREFIX) and exam_name in task.title
        ]

    def test_one_task_per_day_with_due_date_and_instructions(self):
        plan = self._plan()
        created = planner.save_plan_tasks(plan)
        try:
            assert len(created) == 3
            assert [t.due_date for t in created] == [d.date for d in plan.days]
            assert all(t.priority in ("low", "medium", "high") for t in created)
            assert "Reading: p. 4." in created[0].description
            assert "Read 1." in created[0].description
            assert "DB Systems" in created[0].title
        finally:
            for task in created:
                database.delete_task(task.id)

    def test_rebuilding_the_same_plan_does_not_duplicate_tasks(self):
        plan = self._plan()
        first = planner.save_plan_tasks(plan)
        try:
            second = planner.save_plan_tasks(plan)
            assert {t.id for t in first} == {t.id for t in second}
            assert len(self._plan_tasks("DB Systems")) == 3
        finally:
            for task in first:
                database.delete_task(task.id)

    def test_urgent_days_rank_higher(self):
        plan = planner.StudyPlanResult(
            exam_name="DB Systems",
            exam_date=date(2026, 10, 9),
            total_days=6,
            hours_per_day=2.0,
            days=[day(n) for n in range(1, 7)],
        )
        created = planner.save_plan_tasks(plan)
        try:
            assert created[0].priority == "low"
            assert created[2].priority == "medium"
            assert created[-1].priority == "high"
        finally:
            for task in created:
                database.delete_task(task.id)

    def test_a_different_exam_gets_its_own_tasks(self):
        first = self._plan()
        second = planner.StudyPlanResult(
            exam_name="Networks",
            exam_date=date(2026, 10, 9),
            total_days=1,
            hours_per_day=1.0,
            days=[day(1)],
        )
        created = planner.save_plan_tasks(first) + planner.save_plan_tasks(second)
        try:
            assert len({t.title for t in created}) == 4
        finally:
            for task in created:
                database.delete_task(task.id)

    def test_saved_plan_can_be_reopened(self):
        plan = self._plan()
        created = planner.save_plan_tasks(plan)
        row = None
        try:
            row = database.save_study_plan(
                "DB Systems",
                date(2026, 10, 9),
                planner.render_plan_markdown(plan),
                2.0,
                "",
                3,
            )
            assert row.total_days == 3
            assert "Day 1" in row.plan_text
        finally:
            for task in created:
                database.delete_task(task.id)
            if row is not None:
                database.delete_study_plan(row.id)
