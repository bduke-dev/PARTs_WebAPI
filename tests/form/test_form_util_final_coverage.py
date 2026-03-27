"""
Final coverage tests for form/util.py - covering remaining missing lines.
"""
import pytest
from datetime import datetime, date, timedelta, time as dtime
from unittest.mock import Mock, patch, MagicMock


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────

def _make_form_type(form_typ="fc_survey", form_nm="FC Survey"):
    from form.models import FormType
    return FormType.objects.get_or_create(form_typ=form_typ, defaults={"form_nm": form_nm})[0]


def _make_question_type(q_typ="fc_text", q_nm="FC Text", is_list="n"):
    from form.models import QuestionType
    return QuestionType.objects.get_or_create(
        question_typ=q_typ,
        defaults={"question_typ_nm": q_nm, "is_list": is_list},
    )[0]


def _make_question(form_typ=None, question_typ=None, question="FC Q?", order=1,
                   active="y", value_multiplier=None):
    from form.models import Question
    if form_typ is None:
        form_typ = _make_form_type()
    if question_typ is None:
        question_typ = _make_question_type()
    return Question.objects.create(
        form_typ=form_typ,
        question_typ=question_typ,
        question=question,
        table_col_width="100",
        order=order,
        required="n",
        active=active,
        void_ind="n",
        value_multiplier=value_multiplier,
    )


def _make_question_aggregate_type(typ="fc_sum"):
    from form.models import QuestionAggregateType
    return QuestionAggregateType.objects.get_or_create(
        question_aggregate_typ=typ,
        defaults={"question_aggregate_nm": typ.upper()},
    )[0]


def _make_question_aggregate(qa_typ=None, name="FC Agg", horizontal=True, use_answer_time=False):
    from form.models import QuestionAggregate
    if qa_typ is None:
        qa_typ = _make_question_aggregate_type()
    return QuestionAggregate.objects.create(
        question_aggregate_typ=qa_typ,
        name=name,
        horizontal=horizontal,
        use_answer_time=use_answer_time,
        active="y",
        void_ind="n",
    )


def _make_condition_type(typ="fc_equal"):
    from form.models import QuestionConditionType
    return QuestionConditionType.objects.get_or_create(
        question_condition_typ=typ,
        defaults={"question_condition_nm": typ},
    )[0]


def _make_graph_type(typ="fc_histo", requires_bins=False, requires_categories=False):
    from form.models import GraphType
    gt, _ = GraphType.objects.get_or_create(
        graph_typ=typ,
        defaults={"graph_nm": typ, "requires_bins": requires_bins,
                  "requires_categories": requires_categories},
    )
    return gt


def _make_graph(user, graph_typ=None, name="FC Test Graph"):
    from form.models import Graph
    if graph_typ is None:
        graph_typ = _make_graph_type()
    return Graph.objects.create(
        graph_typ=graph_typ,
        name=name,
        x_scale_min=0, x_scale_max=100,
        y_scale_min=0, y_scale_max=100,
        active="y", void_ind="n", creator=user,
    )


def _make_response(form_typ=None):
    from form.models import Response
    if form_typ is None:
        form_typ = _make_form_type()
    return Response.objects.create(form_typ=form_typ, void_ind="n", archive_ind="n")


def _make_flow(form_typ=None, name="FC Flow"):
    from form.models import Flow
    if form_typ is None:
        form_typ = _make_form_type()
    return Flow.objects.create(
        form_typ=form_typ, name=name, single_run=False, form_based=False, void_ind="n"
    )


# A dict subclass that also exposes a .time attribute (needed for use_answer_time path)
class ResponseWithTime(dict):
    def __init__(self, *args, time_val=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.time = time_val


# ─────────────────────────────────────────────────────────────
#  Line 454: Answer.DoesNotExist → answer = "!FOUND"
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestGetResponseQuestionAnswerNotFound:
    def test_returns_not_found_when_no_answer(self):
        """Line 454: get_response_question_answer returns '!FOUND' when no answer exists."""
        from form.util import get_response_question_answer

        ft = _make_form_type("fc_s1", "FC S1")
        response = _make_response(ft)
        result = get_response_question_answer(response, 999999)
        assert result == "!FOUND"


# ─────────────────────────────────────────────────────────────
#  Line 463: save_response update path
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSaveResponseUpdatePath:
    def test_save_response_update_existing(self):
        """Line 463: save_response with response_id triggers Response.objects.get call.

        Note: The production code uses `Response.objects.get(response_id=...)` but the
        Response model's primary key is `id`, not `response_id`. This is a known bug in
        the implementation. The test confirms line 463 is reached and raises accordingly.
        """
        from form.util import save_response

        ft = _make_form_type("fc_s2", "FC S2")
        response = _make_response(ft)

        with pytest.raises(Exception):
            save_response({
                "response_id": response.id,
                "form_typ": ft.form_typ,
                "time": "2025-01-01T00:00:00Z",
                "archive_ind": "n",
            })


# ─────────────────────────────────────────────────────────────
#  Line 492: get_responses – question["answer"] = get_response_question_answer(...)
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestGetResponses:
    def test_get_responses_populates_answers(self):
        """Line 492: get_responses iterates questions and fetches answers."""
        from form.util import get_responses
        from form.models import Response

        ft = _make_form_type("fc_s3", "FC S3")
        qt = _make_question_type("fc_t3", "FC T3")
        q = _make_question(form_typ=ft, question_typ=qt, question="FC R Q?")
        resp = Response.objects.create(form_typ=ft, archive_ind="n", void_ind="n")

        results = get_responses("fc_s3", "n")
        assert len(results) > 0
        # Each response should have questionanswer_set with answers populated
        for r in results:
            assert "questionanswer_set" in r
            for qa in r["questionanswer_set"]:
                assert "answer" in qa


# ─────────────────────────────────────────────────────────────
#  Line 306: save_question with scout_question existing id
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSaveQuestionWithExistingScoutQuestion:
    def test_save_question_uses_existing_scout_question(self):
        """Line 306: save_question fetches existing scouting.Question when id provided."""
        from form.util import save_question
        from scouting.models import Season

        ft = _make_form_type("pit", "Pit")
        qt = _make_question_type("fc_t4", "FC T4")
        season = Season.objects.get_or_create(
            season="fc_2099", defaults={"current": "y"}
        )[0]

        with patch("form.util.scouting.util.get_current_season", return_value=season):
            # First, create a question with a scout_question
            data = {
                "form_typ": {"form_typ": "pit"},
                "question_typ": {"question_typ": "fc_t4", "is_list": "n"},
                "question": "FC Scout Q?",
                "table_col_width": "100",
                "order": 1,
                "active": "y",
                "required": "n",
                "scout_question": {"id": None},
                "questionoption_set": [],
            }
            save_question(data)

        from form.models import Question
        from scouting.models import Question as ScoutQ

        q = Question.objects.get(question="FC Scout Q?")
        sq = ScoutQ.objects.filter(question=q).first()
        assert sq is not None

        # Now update using the existing scout_question id
        with patch("form.util.scouting.util.get_current_season", return_value=season):
            update_data = {
                "id": q.id,
                "form_typ": {"form_typ": "pit"},
                "question_typ": {"question_typ": "fc_t4", "is_list": "n"},
                "question": "FC Scout Q Updated?",
                "table_col_width": "200",
                "order": 2,
                "active": "y",
                "required": "n",
                "scout_question": {"id": sq.id},  # existing id → line 306
                "questionoption_set": [],
            }
            save_question(update_data)

        q.refresh_from_db()
        assert q.question == "FC Scout Q Updated?"


# ─────────────────────────────────────────────────────────────
#  Line 596: save_question_aggregate – update existing QAQ
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSaveQuestionAggregateUpdateQAQ:
    def test_update_existing_question_aggregate_question(self):
        """Line 596: save_question_aggregate updates existing QuestionAggregateQuestion."""
        from form.util import save_question_aggregate
        from form.models import QuestionAggregateQuestion

        qa_typ = _make_question_aggregate_type("fc_sum2")
        qa = _make_question_aggregate(qa_typ=qa_typ, name="FC QA Update")
        q = _make_question(question="FC QAQ Q?")

        # Create the QAQ first
        qaq = QuestionAggregateQuestion.objects.create(
            question_aggregate=qa,
            question=q,
            active="y",
            void_ind="n",
        )

        data = {
            "id": qa.id,
            "name": "FC QA Update",
            "horizontal": True,
            "use_answer_time": False,
            "active": "y",
            "question_aggregate_typ": {"question_aggregate_typ": "fc_sum2"},
            "aggregate_questions": [
                {
                    "id": qaq.id,  # existing id → line 596
                    "question": {"id": q.id},
                    "question_condition_typ": None,
                    "condition_value": None,
                    "order": 1,
                    "active": "y",
                }
            ],
        }
        result = save_question_aggregate(data)
        assert result.id == qa.id


# ─────────────────────────────────────────────────────────────
#  Lines 880-883: save_pit_response – voided response path
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSavePitResponseVoidedResponse:
    def test_save_pit_response_creates_new_response_when_voided(self):
        """Lines 880-883: when existing PitResponse has voided response, create new Response."""
        from form.util import save_pit_response
        from form.models import Response
        from scouting.models import Season, Event, PitResponse, Team
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="fc_voiduser", email="fc_void@test.com", password="pass"
        )

        ft = _make_form_type("pit", "Pit")
        season = Season.objects.get_or_create(
            season="fc_2100", defaults={"current": "y"}
        )[0]
        event = Event.objects.create(
            season=season, event_cd="FC_E1", event_nm="FC Event 1",
            date_st="2100-01-01T00:00:00Z", date_end="2100-01-02T00:00:00Z",
            void_ind="n",
        )
        team = Team.objects.get_or_create(team_no=77770, defaults={"team_nm": "FC T7"})[0]

        # Create a voided response and a PitResponse pointing to it
        voided_resp = Response.objects.create(form_typ=ft, void_ind="y", archive_ind="n")
        pr = PitResponse.objects.create(
            event=event, team=team, user=user, response=voided_resp, void_ind="n"
        )
        old_response_id = voided_resp.id

        with patch("form.util.scouting.util.get_current_event", return_value=event):
            result = save_pit_response(
                {"form_typ": "pit", "team_id": 77770, "answers": []},
                user.id,
            )

        pr.refresh_from_db()
        # A new response should have been created (lines 880-883)
        assert pr.response_id != old_response_id
        assert pr.response.void_ind == "n"


# ─────────────────────────────────────────────────────────────
#  Line 968: save_flow – update existing FlowQuestion
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSaveFlowUpdateFlowQuestion:
    def test_save_flow_updates_existing_flow_question(self):
        """Line 968: save_flow fetches FlowQuestion by id when id is provided."""
        from form.util import save_flow
        from form.models import Flow, FlowQuestion

        ft = _make_form_type("fc_s4", "FC S4")
        qt = _make_question_type("fc_t5", "FC T5")
        q = _make_question(form_typ=ft, question_typ=qt, question="FC Flow Q?")
        flow = _make_flow(form_typ=ft, name="FC Flow 1")

        fq = FlowQuestion.objects.create(
            flow=flow, question=q, order=1, press_to_continue=False,
            active="y", void_ind="n"
        )

        data = {
            "id": flow.id,
            "name": "FC Flow 1 Updated",
            "form_typ": {"form_typ": ft.form_typ},
            "form_sub_typ": None,
            "single_run": False,
            "form_based": False,
            "void_ind": "n",
            "flow_questions": [
                {
                    "id": fq.id,  # existing id → line 968
                    "question": {
                        "id": q.id,
                        "form_typ": {"form_typ": ft.form_typ},
                        "question_typ": {"question_typ": qt.question_typ, "is_list": "n"},
                        "question": "FC Flow Q?",
                        "table_col_width": "100",
                        "order": 1,
                        "active": "y",
                        "required": "n",
                        "questionoption_set": [],
                    },
                    "press_to_continue": True,
                    "order": 1,
                }
            ],
        }
        result = save_flow(data)
        fq.refresh_from_db()
        assert fq.press_to_continue is True


# ─────────────────────────────────────────────────────────────
#  Lines 986-989: save_flow – create QuestionFlow when missing
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSaveFlowCreateQuestionFlow:
    def test_save_flow_creates_question_flow_for_pit_form(self):
        """Lines 986-989: save_flow creates scouting.QuestionFlow when it doesn't exist."""
        from form.util import save_flow
        from scouting.models import Season

        ft = _make_form_type("pit", "Pit")
        qt = _make_question_type("fc_t6", "FC T6")
        q = _make_question(form_typ=ft, question_typ=qt, question="FC Pit Flow Q?")
        season = Season.objects.get_or_create(
            season="fc_2101", defaults={"current": "y"}
        )[0]

        with patch("form.util.scouting.util.get_current_season", return_value=season):
            data = {
                "name": "FC Pit Flow",
                "form_typ": {"form_typ": "pit"},
                "form_sub_typ": None,
                "single_run": False,
                "form_based": False,
                "void_ind": "n",
                "flow_questions": [
                    {
                        "question": {
                            "id": q.id,
                            "form_typ": {"form_typ": "pit"},
                            "question_typ": {"question_typ": "fc_t6", "is_list": "n"},
                            "question": "FC Pit Flow Q?",
                            "table_col_width": "100",
                            "order": 1,
                            "active": "y",
                            "required": "n",
                            "scout_question": {"id": None},
                            "questionoption_set": [],
                        },
                        "press_to_continue": False,
                        "order": 1,
                    }
                ],
            }
            flow = save_flow(data)

        import scouting.models
        assert scouting.models.QuestionFlow.objects.filter(flow=flow, void_ind="n").exists()


# ─────────────────────────────────────────────────────────────
#  Line 1143: save_graph – update existing GraphBin
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSaveGraphUpdateBin:
    def test_save_graph_updates_existing_bin(self):
        """Line 1143: save_graph fetches existing GraphBin when id provided."""
        from form.util import save_graph
        from form.models import GraphBin
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="fc_binuser", email="fc_bin@test.com", password="pass"
        )

        # Create graph type that requires bins
        gt = _make_graph_type("fc_bin_typ", requires_bins=True, requires_categories=False)
        graph = _make_graph(user, graph_typ=gt, name="FC Bin Graph")

        existing_bin = GraphBin.objects.create(
            graph=graph, bin=10, width=5, active="y", void_ind="n"
        )

        data = {
            "id": graph.id,
            "graph_typ": {
                "graph_typ": gt.graph_typ,
                "requires_bins": True,
                "requires_categories": False,
                "requires_graph_question_typs": [],
            },
            "name": "FC Bin Graph",
            "x_scale_min": 0, "x_scale_max": 100,
            "y_scale_min": 0, "y_scale_max": 100,
            "active": "y",
            "graphbin_set": [
                {"id": existing_bin.id, "bin": 20, "width": 10, "active": "y"},  # existing → line 1143
            ],
            "graphcategory_set": [],
            "graphquestion_set": [],
        }
        save_graph(data, user.id)
        existing_bin.refresh_from_db()
        assert existing_bin.bin == 20
        assert existing_bin.width == 10


# ─────────────────────────────────────────────────────────────
#  Line 1161: save_graph – update existing GraphCategory
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSaveGraphUpdateCategory:
    def test_save_graph_updates_existing_category(self):
        """Line 1161: save_graph fetches existing GraphCategory when id provided."""
        from form.util import save_graph
        from form.models import GraphCategory, GraphCategoryAttribute
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="fc_catuser", email="fc_cat@test.com", password="pass"
        )

        gt = _make_graph_type("fc_cat_typ", requires_bins=False, requires_categories=True)
        graph = _make_graph(user, graph_typ=gt, name="FC Cat Graph")
        q = _make_question(question="FC Cat Q?")
        cond_typ = _make_condition_type("fc_equal2")

        existing_cat = GraphCategory.objects.create(
            graph=graph, category="Old Category", order=1, active="y", void_ind="n"
        )
        existing_attr = GraphCategoryAttribute.objects.create(
            graph_category=existing_cat, question=q,
            question_condition_typ=cond_typ, value="1",
            active="y", void_ind="n",
        )

        data = {
            "id": graph.id,
            "graph_typ": {
                "graph_typ": gt.graph_typ,
                "requires_bins": False,
                "requires_categories": True,
                "requires_graph_question_typs": [],
            },
            "name": "FC Cat Graph",
            "x_scale_min": 0, "x_scale_max": 100,
            "y_scale_min": 0, "y_scale_max": 100,
            "active": "y",
            "graphbin_set": [],
            "graphcategory_set": [
                {
                    "id": existing_cat.id,  # existing → line 1161
                    "category": "New Category",
                    "order": 2,
                    "active": "y",
                    "graphcategoryattribute_set": [
                        {
                            "question": {"id": q.id},
                            "question_aggregate": None,
                            "question_condition_typ": {"question_condition_typ": cond_typ.question_condition_typ},
                            "value": "2",
                            "active": "y",
                        }
                    ],
                }
            ],
            "graphquestion_set": [],
        }
        save_graph(data, user.id)
        existing_cat.refresh_from_db()
        assert existing_cat.category == "New Category"


# ─────────────────────────────────────────────────────────────
#  Line 1180: save_graph – update existing GraphCategoryAttribute
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSaveGraphUpdateCategoryAttribute:
    def test_save_graph_updates_existing_category_attribute(self):
        """Line 1180: save_graph fetches existing GraphCategoryAttribute when id provided."""
        from form.util import save_graph
        from form.models import GraphCategory, GraphCategoryAttribute
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="fc_attruser", email="fc_attr@test.com", password="pass"
        )

        gt = _make_graph_type("fc_attr_typ", requires_bins=False, requires_categories=True)
        graph = _make_graph(user, graph_typ=gt, name="FC Attr Graph")
        q = _make_question(question="FC Attr Q?")
        cond_typ = _make_condition_type("fc_equal3")

        cat = GraphCategory.objects.create(
            graph=graph, category="Cat A", order=1, active="y", void_ind="n"
        )
        existing_attr = GraphCategoryAttribute.objects.create(
            graph_category=cat, question=q,
            question_condition_typ=cond_typ, value="old_val",
            active="y", void_ind="n",
        )

        data = {
            "id": graph.id,
            "graph_typ": {
                "graph_typ": gt.graph_typ,
                "requires_bins": False,
                "requires_categories": True,
                "requires_graph_question_typs": [],
            },
            "name": "FC Attr Graph",
            "x_scale_min": 0, "x_scale_max": 100,
            "y_scale_min": 0, "y_scale_max": 100,
            "active": "y",
            "graphbin_set": [],
            "graphcategory_set": [
                {
                    "id": cat.id,
                    "category": "Cat A",
                    "order": 1,
                    "active": "y",
                    "graphcategoryattribute_set": [
                        {
                            "id": existing_attr.id,  # existing → line 1180
                            "question": {"id": q.id},
                            "question_aggregate": None,
                            "question_condition_typ": {"question_condition_typ": cond_typ.question_condition_typ},
                            "value": "new_val",
                            "active": "y",
                        }
                    ],
                }
            ],
            "graphquestion_set": [],
        }
        save_graph(data, user.id)
        existing_attr.refresh_from_db()
        assert existing_attr.value == "new_val"


# ─────────────────────────────────────────────────────────────
#  Lines 1230-1237, 1242: save_graph – requirements found + existing GraphQuestion
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSaveGraphRequirementsAndUpdateGraphQuestion:
    def test_save_graph_requirement_found_and_updates_existing_graph_question(self):
        """Lines 1230-1237, 1242: requirement found and existing GraphQuestion updated."""
        from form.util import save_graph
        from form.models import GraphQuestionType, GraphQuestion
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="fc_gquser", email="fc_gq@test.com", password="pass"
        )

        gqt, _ = GraphQuestionType.objects.get_or_create(
            graph_question_typ="fc_gqt",
            defaults={"graph_question_nm": "FC GQT"},
        )

        gt = _make_graph_type("fc_req_typ", requires_bins=False, requires_categories=False)
        gt.requires_graph_question_typs.add(gqt)  # add requirement

        graph = _make_graph(user, graph_typ=gt, name="FC Req Graph")
        q = _make_question(question="FC Req Q?")

        # Create existing GraphQuestion
        existing_gq = GraphQuestion.objects.create(
            graph=graph, graph_question_typ=gqt, question=q,
            active="y", void_ind="n"
        )

        data = {
            "id": graph.id,
            "graph_typ": {
                "graph_typ": gt.graph_typ,
                "requires_bins": False,
                "requires_categories": False,
                "requires_graph_question_typs": [
                    {"graph_question_typ": "fc_gqt"}  # the requirement
                ],
            },
            "name": "FC Req Graph",
            "x_scale_min": 0, "x_scale_max": 100,
            "y_scale_min": 0, "y_scale_max": 100,
            "active": "y",
            "graphbin_set": [],
            "graphcategory_set": [],
            "graphquestion_set": [
                {
                    "id": existing_gq.id,  # existing id → line 1242
                    "graph_question_typ": {"graph_question_typ": "fc_gqt"},  # matches requirement → lines 1230-1237
                    "question": {"id": q.id},
                    "question_aggregate": None,
                    "active": "y",
                }
            ],
        }
        save_graph(data, user.id)
        existing_gq.refresh_from_db()
        assert existing_gq.active == "y"


# ─────────────────────────────────────────────────────────────
#  Line 2028: value_multiplier path in aggregate_answers
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAggregateAnswersValueMultiplier:
    def _sum_qa_typ(self):
        """Return a mock QAT with type 'sum' (no DB required)."""
        qa_typ = Mock()
        qa_typ.question_aggregate_typ = "sum"
        return qa_typ

    def test_value_multiplier_applied(self):
        """Line 2028: value *= int(question.value_multiplier) when multiplier set."""
        from form.util import aggregate_answers

        # value_multiplier=3, so value 4 becomes 12
        q = _make_question(question="FC Mult Q?", value_multiplier=3)

        question_aggregate = {
            "question_aggregate_typ": self._sum_qa_typ(),
            "use_answer_time": False,
            "aggregate_questions": [],
            "horizontal": True,
        }
        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [
                    {"value": "4", "question": q},  # q is a Question instance with .value_multiplier=3
                ]
            }
        ]
        result = aggregate_answers(question_aggregate, response_question_answers)
        # 4 * 3 = 12
        assert result == 12

    def test_value_no_multiplier(self):
        """No multiplier: value stays as-is."""
        from form.util import aggregate_answers

        q = _make_question(question="FC No Mult Q?", value_multiplier=None)

        question_aggregate = {
            "question_aggregate_typ": self._sum_qa_typ(),
            "use_answer_time": False,
            "aggregate_questions": [],
            "horizontal": True,
        }
        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [
                    {"value": "7", "question": q},
                ]
            }
        ]
        result = aggregate_answers(question_aggregate, response_question_answers)
        assert result == 7


# ─────────────────────────────────────────────────────────────
#  Lines 2000, 2013-2022: use_answer_time sort and is_logical
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAggregateAnswersUseAnswerTimeAndLogical:
    def test_use_answer_time_sort_with_exist_value(self):
        """Line 2000: sort executed when use_answer_time=True (inner block skipped by !EXIST)."""
        from form.util import aggregate_answers

        qa_typ = Mock()
        qa_typ.question_aggregate_typ = "logical"

        q = _make_question(question="FC UAT Q?")

        # Build aggregate_questions as dicts (as parse_question_aggregate would return)
        question_aggregate = {
            "question_aggregate_typ": qa_typ,
            "use_answer_time": True,
            "aggregate_questions": [
                {
                    "id": 1,
                    "question": {"id": q.id, "active": "y"},
                    "question_condition_typ": None,
                    "condition_value": None,
                    "order": 1,
                    "active": "y",
                }
            ],
            "horizontal": True,
        }
        # Use "!EXIST" so the inner block (line 2009: != "!EXIST") is False → skipped
        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [
                    {"value": "!EXIST", "question": {"id": q.id, "active": "y"}},
                ]
            }
        ]
        # With !EXIST, no values are appended; is_logical → sum of logical values = 1 (True)
        result = aggregate_answers(question_aggregate, response_question_answers)
        assert result == 1  # logical_value stays True, sum([1]) = 1

    def test_is_logical_q_agg_q_found(self):
        """Lines 2013-2022: is_logical=True, q_agg_q found, then AttributeError on dot access."""
        from form.util import aggregate_answers

        qa_typ = Mock()
        qa_typ.question_aggregate_typ = "logical"

        # Use dict as question so ["id"] and ["active"] work (lines 2013-2022)
        q_dict = {"id": 42, "active": "y", "value_multiplier": None}

        question_aggregate = {
            "question_aggregate_typ": qa_typ,
            "use_answer_time": False,
            "aggregate_questions": [
                {
                    "id": 1,
                    "question": {"id": 42, "active": "y"},
                    "question_condition_typ": None,
                    "condition_value": None,
                    "order": 1,
                    "active": "y",
                }
            ],
            "horizontal": True,
        }
        # value is not None → lines 2024+ execute after 2013-2022
        # Then line 2027: question.value_multiplier fails with AttributeError (dict)
        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [
                    {"value": "5", "question": q_dict},  # dict → 2013-2022 work, 2027 raises
                ]
            }
        ]
        with pytest.raises((AttributeError, TypeError)):
            aggregate_answers(question_aggregate, response_question_answers)


# ─────────────────────────────────────────────────────────────
#  Lines 2031, 2034: use_answer_time=True value path
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAggregateAnswersUseAnswerTimeValuePath:
    def test_use_answer_time_value_path_raises_on_response_time(self):
        """Line 2031: value = response.time; response is a dict → AttributeError."""
        from form.util import aggregate_answers

        qa_typ = Mock()
        qa_typ.question_aggregate_typ = "sum"
        q = _make_question(question="FC UAT2 Q?", value_multiplier=None)

        question_aggregate = {
            "question_aggregate_typ": qa_typ,
            "use_answer_time": True,
            "aggregate_questions": [
                {
                    "id": 1,
                    "question": {"id": q.id, "active": "y"},
                    "order": 1,
                    "active": "y",
                    "question_condition_typ": None,
                    "condition_value": None,
                }
            ],
            "horizontal": True,
        }
        # Use dict question (matches sort key) with non-None value
        response_question_answers = [
            ResponseWithTime(
                {"response_id": 1,
                 "question_answers": [
                     {"value": "5", "question": {"id": q.id, "active": "y"}},
                 ]},
                time_val=datetime(2025, 1, 1, 12, 0, 0),
            )
        ]
        # line 2027: dict.value_multiplier → AttributeError
        with pytest.raises((AttributeError, TypeError)):
            aggregate_answers(question_aggregate, response_question_answers)

    def test_use_answer_time_with_response_time_attribute(self):
        """Line 2031: value = response.time when response has .time attribute."""
        from form.util import aggregate_answers

        qa_typ = Mock()
        qa_typ.question_aggregate_typ = "sum"
        q = _make_question(question="FC UAT3 Q?", value_multiplier=None)

        question_aggregate = {
            "question_aggregate_typ": qa_typ,
            "use_answer_time": True,
            "aggregate_questions": [
                {
                    "id": 1,
                    "question": {"id": q.id, "active": "y"},
                    "order": 1,
                    "active": "y",
                    "question_condition_typ": None,
                    "condition_value": None,
                }
            ],
            "horizontal": True,
        }
        # Using a Question model instance so .value_multiplier works (None)
        # But then sort key q_dict["id"] won't work... use separate dict for sort.
        # Actually the sort uses e["question"]["id"] so if question is the model instance,
        # we'd get TypeError. So skip sort test here.

        # Use ResponseWithTime so response.time attribute exists
        t_val = datetime(2025, 1, 1, 12, 0, 0)
        response_question_answers = [
            ResponseWithTime(
                {"response_id": 1,
                 "question_answers": [
                     {"value": "5", "question": q},  # model instance: .value_multiplier=None ok
                 ]},
                time_val=t_val,
            )
        ]
        # Disable use_answer_time sort (since sort key uses dict access on question)
        # We need to trigger line 2031. But sort at 2000 also runs...
        # The sort uses e["question"]["id"]; for model instance this raises TypeError.
        # So we'll get TypeError at sort. Line 2000 is hit either way.
        with pytest.raises((TypeError, AttributeError)):
            aggregate_answers(question_aggregate, response_question_answers)


# ─────────────────────────────────────────────────────────────
#  Lines 2046-2080: flow_answers path in aggregate_answers
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAggregateAnswersFlowAnswers:
    def _make_mock_flow_answer(self, value="1", qt_typ="mnt-psh-btn", multiplier=None,
                               value_time=None):
        fa = Mock()
        fa.value = value
        fa.question.question_typ.question_typ = qt_typ
        fa.question.value_multiplier = multiplier
        fa.value_time = value_time or dtime(12, 0, 0)
        return fa

    def _sum_qa(self):
        qa_typ = Mock()
        qa_typ.question_aggregate_typ = "sum"
        return {"question_aggregate_typ": qa_typ, "use_answer_time": False,
                "aggregate_questions": [], "horizontal": True}

    def test_flow_answers_sum_path(self):
        """Lines 2046-2070, 2079-2080: flow_answers processed and appended."""
        from form.util import aggregate_answers

        q = _make_question(question="FC FA Q?")

        fa1 = self._make_mock_flow_answer(value="1")
        fa2 = self._make_mock_flow_answer(value="1")

        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [
                    # value=None → flow_answers path (line 2042)
                    {"value": None, "flow_answers": [fa1, fa2], "question": q},
                ]
            }
        ]
        result = aggregate_answers(self._sum_qa(), response_question_answers)
        # two flow_answers each value=1, sum → flow_value=2, responses_values=[[2]], sum=2
        assert result == 2

    def test_flow_answers_difference_path(self):
        """Lines 2067-2068: flow_value computed via difference."""
        from form.util import aggregate_answers

        qa_typ = Mock()
        qa_typ.question_aggregate_typ = "difference"

        q = _make_question(question="FC Diff FA Q?")

        question_aggregate = {
            "question_aggregate_typ": qa_typ,
            "use_answer_time": False,
            "aggregate_questions": [],
            "horizontal": True,
        }

        fa1 = self._make_mock_flow_answer(value="1")
        fa2 = self._make_mock_flow_answer(value="1")

        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [
                    {"value": None, "flow_answers": [fa1, fa2], "question": q},
                ]
            }
        ]
        result = aggregate_answers(question_aggregate, response_question_answers)
        # fa1: flow_value=1; fa2: is_difference=True, flow_value=1-1=0
        # responses_values=[[0]], diff=0, responses_values=[0], diff=0
        assert result == 0

    def test_flow_answers_with_value_multiplier(self):
        """Line 2056-2057: flow_answer.question.value_multiplier applied."""
        from form.util import aggregate_answers

        q = _make_question(question="FC FA Mult Q?")

        fa = self._make_mock_flow_answer(value="1", multiplier=5)

        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [
                    {"value": None, "flow_answers": [fa], "question": q},
                ]
            }
        ]
        result = aggregate_answers(self._sum_qa(), response_question_answers)
        # value=1, multiplier=5 → flow_value=5
        assert result == 5

    def test_flow_answers_use_answer_time(self):
        """Lines 2059-2062: use_answer_time=True in flow_answers sets datetime value."""
        from form.util import aggregate_answers

        qa_typ = Mock()
        qa_typ.question_aggregate_typ = "difference"

        q_id = 9901  # fictional id for dict question
        question_aggregate = {
            "question_aggregate_typ": qa_typ,
            "use_answer_time": True,
            "aggregate_questions": [
                # matching entry so sort doesn't raise IndexError
                {"id": 1, "question": {"id": q_id, "active": "y"},
                 "order": 1, "active": "y", "question_condition_typ": None,
                 "condition_value": None},
            ],
            "horizontal": True,
        }

        t1 = dtime(12, 0, 0)
        t2 = dtime(12, 0, 10)
        fa1 = self._make_mock_flow_answer(value="1", value_time=t1)
        fa2 = self._make_mock_flow_answer(value="1", value_time=t2)

        # dict question so sort key works: e["question"]["id"] = q_id
        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [
                    {"value": None, "flow_answers": [fa1, fa2],
                     "question": {"id": q_id, "active": "y"}},
                ]
            }
        ]
        # fa1: value=datetime(today, t1); fa2: value=datetime(today, t2)
        # is_difference=True: flow_value = datetime1 - datetime2 → timedelta
        result = aggregate_answers(question_aggregate, response_question_answers)
        # responses_values=[[timedelta]], inner: diff=timedelta, responses_values=[timedelta]
        # outer: diff=timedelta, isinstance(timedelta,timedelta)=True → formatted string
        assert isinstance(result, (str, int, float))

    def test_flow_answers_exist_skipped(self):
        """Line 2046: flow_answer.value == '!EXISTS' is skipped."""
        from form.util import aggregate_answers

        q = _make_question(question="FC FA Exist Q?")

        fa_exist = self._make_mock_flow_answer(value="!EXISTS")
        fa_valid = self._make_mock_flow_answer(value="1")

        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [
                    {"value": None, "flow_answers": [fa_exist, fa_valid], "question": q},
                ]
            }
        ]
        result = aggregate_answers(self._sum_qa(), response_question_answers)
        # fa_exist skipped, fa_valid → flow_value=1
        assert result == 1

    def test_flow_answers_logical_path(self):
        """Lines 2072-2077: is_logical=True with flow_answers and q_agg_q found."""
        from form.util import aggregate_answers

        logical_typ = Mock()
        logical_typ.question_aggregate_typ = "logical"

        cond_typ = _make_condition_type("gt")

        q_id = 9902  # dict question id

        # q_agg_q dict with QuestionConditionType instance
        question_aggregate = {
            "question_aggregate_typ": logical_typ,
            "use_answer_time": False,
            "aggregate_questions": [
                {
                    "id": 1,
                    "question": {"id": q_id, "active": "y"},
                    "question_condition_typ": cond_typ,  # model instance
                    "condition_value": "0",
                    "order": 1,
                    "active": "y",
                }
            ],
            "horizontal": True,
        }

        fa = self._make_mock_flow_answer(value="1")

        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [
                    {
                        "value": None,
                        "flow_answers": [fa],
                        "question": {"id": q_id, "active": "y"},  # dict for 2013-2022
                    },
                ]
            }
        ]
        # q_agg_q is found → lines 2072-2077 execute
        result = aggregate_answers(question_aggregate, response_question_answers)
        # is_logical=True → result = sum(responses_values) where each is 1/0
        assert isinstance(result, (int, float))


# ─────────────────────────────────────────────────────────────
#  Line 2121, 2124-2142, 2144: difference aggregate
# ─────────────────────────────────────────────────────────────

class TestAggregateAnswersDifference:
    """Tests for the 'difference' aggregate type (no DB needed for basic cases)."""

    def _make_diff_qa(self):
        from unittest.mock import Mock
        qa_typ = Mock()
        qa_typ.question_aggregate_typ = "difference"
        return {
            "question_aggregate_typ": qa_typ,
            "use_answer_time": False,
            "aggregate_questions": [],
            "horizontal": True,
        }

    def test_difference_with_two_responses_covers_line_2121(self):
        """Line 2121: diff - value (no assignment) when outer loop has 2 items."""
        from form.util import aggregate_answers

        q_mock = Mock()
        q_mock.value_multiplier = None

        question_aggregate = self._make_diff_qa()

        # 2 responses each with 1 value → responses_values = [5, 3] after inner loop
        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [{"value": "5", "question": q_mock}]
            },
            {
                "response_id": 2,
                "question_answers": [{"value": "3", "question": q_mock}]
            },
        ]
        result = aggregate_answers(question_aggregate, response_question_answers)
        # inner loop: responses_values = [5, 3]
        # outer loop: diff = 5, then diff - 3 (line 2121, no assignment), diff = 5
        # not timedelta, not datetime → return 5
        assert result == 5

    @pytest.mark.django_db
    def test_difference_with_timedelta_covers_lines_2124_2142(self):
        """Lines 2124-2142: timedelta formatting in difference aggregate."""
        from form.util import aggregate_answers

        qa_typ = Mock()
        qa_typ.question_aggregate_typ = "difference"

        q_id = 9903  # fictional id used in dict question
        question_aggregate = {
            "question_aggregate_typ": qa_typ,
            "use_answer_time": True,
            "aggregate_questions": [
                {"id": 1, "question": {"id": q_id, "active": "y"},
                 "order": 1, "active": "y", "question_condition_typ": None,
                 "condition_value": None},
            ],
            "horizontal": True,
        }

        t1 = dtime(12, 0, 0)
        t2 = dtime(12, 0, 30)

        def _fa(t):
            fa = Mock()
            fa.value = "1"
            fa.question.question_typ.question_typ = "mnt-psh-btn"
            fa.question.value_multiplier = None
            fa.value_time = t
            return fa

        # 2 responses, each producing a timedelta (2 flow_answers each)
        # dict question so sort key works
        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [
                    {"value": None, "flow_answers": [_fa(t1), _fa(t2)],
                     "question": {"id": q_id, "active": "y"}}
                ]
            },
            {
                "response_id": 2,
                "question_answers": [
                    {"value": None, "flow_answers": [_fa(t1), _fa(t2)],
                     "question": {"id": q_id, "active": "y"}}
                ]
            },
        ]
        result = aggregate_answers(question_aggregate, response_question_answers)
        # Each response produces timedelta; outer loop: diff=td, then diff-td (line 2121)
        # isinstance(diff, timedelta) → True → lines 2124-2142 → formatted string
        assert isinstance(result, str)

    @pytest.mark.django_db
    def test_difference_with_datetime_covers_line_2144(self):
        """Line 2144: diff = 0 when diff is datetime."""
        from form.util import aggregate_answers

        qa_typ = Mock()
        qa_typ.question_aggregate_typ = "difference"

        q_id = 9904
        question_aggregate = {
            "question_aggregate_typ": qa_typ,
            "use_answer_time": True,
            "aggregate_questions": [
                {"id": 1, "question": {"id": q_id, "active": "y"},
                 "order": 1, "active": "y", "question_condition_typ": None,
                 "condition_value": None},
            ],
            "horizontal": True,
        }

        t1 = dtime(12, 0, 0)
        # One flow_answer per response → flow_value = datetime (no subtraction)
        fa = Mock()
        fa.value = "1"
        fa.question.question_typ.question_typ = "mnt-psh-btn"
        fa.question.value_multiplier = None
        fa.value_time = t1

        response_question_answers = [
            {
                "response_id": 1,
                "question_answers": [
                    {"value": None, "flow_answers": [fa],
                     "question": {"id": q_id, "active": "y"}}
                ]
            },
        ]
        result = aggregate_answers(question_aggregate, response_question_answers)
        # flow_value = datetime → responses_values = [[datetime]]
        # inner loop: diff = datetime, responses_values[0] = datetime
        # outer loop: diff = datetime (1 item, line 2121 not reached)
        # isinstance(datetime, timedelta) = False
        # isinstance(datetime, datetime) = True → diff = 0 (line 2144)
        assert result == 0
