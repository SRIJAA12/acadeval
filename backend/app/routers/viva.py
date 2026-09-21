import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import DB, CurrentStudent, CurrentUser
from app.models.project import Project
from app.models.viva import VivaSession
from app.schemas.viva import (
    StartVivaRequest,
    StartVivaResponse,
    VivaQuestion,
    VivaAnswerSubmit,
    VivaAnswerResult,
    AnswerEvaluation,
    VivaReport,
    VivaSessionStatus,
)
from app.services.viva_engine import (
    question_generator,
    semantic_evaluator,
    adaptive_selector,
    kcs_calculator,
    viva_report_gen,
    decode_question_pool,
    encode_question_pool,
    decode_answer_records,
    encode_answer_records,
    AnswerRecord,
    DIFFICULTY_ORDER,
    KCS_COMPLETION_THRESHOLD,
)

router = APIRouter(prefix="/viva", tags=["Intelligent Viva Engine"])


@router.post("/session/start", response_model=StartVivaResponse, status_code=status.HTTP_201_CREATED)
def start_viva_session(payload: StartVivaRequest, current_user: CurrentStudent, db: DB):
    """
    Starts a new research-grade Intelligent Viva Assessment Session for a project.
    Generates a full question pool based on the project's Knowledge Graph and extracted entities.
    """
    project = db.query(Project).filter(
        Project.id == uuid.UUID(payload.projectId),
        Project.student_id == current_user.id,
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    entities = project.extracted_entities or {}
    
    # 1. Generate full question pool from project knowledge graph
    pool_nodes = question_generator.generate_pool(project.title, entities)
    if not pool_nodes:
        raise HTTPException(status_code=400, detail="Could not generate questions: project has insufficient extracted concepts")

    # 2. Select initial question matching startDifficulty
    start_diff = payload.startDifficulty
    initial_q = next((q for q in pool_nodes if q.difficulty == start_diff), pool_nodes[0])

    # 3. Create VivaSession record
    session = VivaSession(
        project_id=project.id,
        questions=encode_question_pool(pool_nodes),
        answers=[],
        scores=[],
        kcs=0.0,
        current_difficulty=initial_q.difficulty,
        difficulty_progression=[initial_q.difficulty],
        consecutive_correct=0,
        consecutive_wrong=0,
        is_complete=False,
        total_score=None,
        report=None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    total_concepts = len({q.target_concept for q in pool_nodes})

    return StartVivaResponse(
        sessionId=str(session.id),
        projectId=str(project.id),
        projectTitle=project.title,
        totalConcepts=total_concepts,
        firstQuestion=VivaQuestion(
            questionId=initial_q.question_id,
            text=initial_q.text,
            category=initial_q.category,
            difficulty=initial_q.difficulty,
            targetConcept=initial_q.target_concept,
        ),
        message="Adaptive Viva Session initialized. First question served.",
    )


@router.post("/answer", response_model=VivaAnswerResult)
def submit_viva_answer(payload: VivaAnswerSubmit, current_user: CurrentStudent, db: DB):
    """
    Submits an answer for the current question in an active viva session.
    
    Workflow:
      1. Evaluates answer using Semantic Similarity (sentence-transformers / Gemini fallback)
      2. Computes multi-dimensional scores (Correctness, Completeness, Depth, Confidence)
      3. Updates Knowledge Coverage Score (KCS)
      4. Adjusts Computerized Adaptive Testing (CAT) difficulty level
      5. Selects next question or finalizes session if coverage target or limit reached
    """
    session = db.query(VivaSession).filter(VivaSession.id == uuid.UUID(payload.sessionId)).first()
    if not session:
        raise HTTPException(status_code=404, detail="Viva session not found")

    if session.is_complete:
        raise HTTPException(status_code=400, detail="This viva session is already complete.")

    pool = decode_question_pool(session.questions)
    answer_records = decode_answer_records(session.answers)

    # Find target question in pool
    question = next((q for q in pool if q.question_id == payload.questionId), None)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found in this session's pool")

    # 1. Semantic evaluation
    eval_dict = semantic_evaluator.evaluate(
        student_answer=payload.answer,
        reference_answer=question.reference_answer,
        expected_keywords=question.expected_keywords,
        question_text=question.text,
        difficulty=question.difficulty,
    )

    # 2. Build AnswerRecord
    record = AnswerRecord(
        question_id=question.question_id,
        target_concept=question.target_concept,
        category=question.category,
        difficulty=question.difficulty,
        answer_text=payload.answer,
        correctness=eval_dict["correctness"],
        completeness=eval_dict["completeness"],
        technical_depth=eval_dict["technical_depth"],
        confidence=eval_dict["confidence"],
        overall_score=eval_dict["overall_score"],
    )
    answer_records.append(record)

    # 3. Update Adaptive Difficulty state
    is_correct = eval_dict["overall_score"] >= adaptive_selector.CORRECT_THRESHOLD
    if is_correct:
        session.consecutive_correct += 1
        session.consecutive_wrong = 0
    else:
        session.consecutive_wrong += 1
        session.consecutive_correct = 0

    curr_level = DIFFICULTY_ORDER.get(session.current_difficulty, 1)

    # 4. Compute updated KCS
    total_concepts = len({q.target_concept for q in pool})
    current_kcs = kcs_calculator.compute(answer_records, total_concepts)
    covered_concepts = kcs_calculator.get_covered_concepts(answer_records)
    answered_ids = {r.question_id for r in answer_records}

    # 5. Select next question or terminate
    next_q_node = adaptive_selector.select_next(
        pool=pool,
        answered_ids=answered_ids,
        covered_concepts=covered_concepts,
        current_difficulty_level=curr_level,
        consecutive_correct=session.consecutive_correct,
        consecutive_wrong=session.consecutive_wrong,
    )

    should_finish = adaptive_selector.should_terminate(
        questions_answered=len(answer_records),
        kcs=current_kcs,
        pool_exhausted=(next_q_node is None),
    )

    # Update session DB model
    session.answers = encode_answer_records(answer_records)
    session.kcs = current_kcs

    next_viva_q = None
    if next_q_node and not should_finish:
        session.current_difficulty = next_q_node.difficulty
        session.difficulty_progression.append(next_q_node.difficulty)
        next_viva_q = VivaQuestion(
            questionId=next_q_node.question_id,
            text=next_q_node.text,
            category=next_q_node.category,
            difficulty=next_q_node.difficulty,
            targetConcept=next_q_node.target_concept,
        )
    else:
        session.is_complete = True
        # Generate final viva report
        report_dict = viva_report_gen.generate(
            session_id=str(session.id),
            project_id=str(session.project_id),
            project_title=session.project.title if session.project else "Project Viva",
            answer_records=answer_records,
            pool=pool,
            difficulty_progression=session.difficulty_progression or [session.current_difficulty],
            kcs=current_kcs,
        )
        session.report = report_dict
        session.total_score = report_dict.get("overallScore", 0.0)

    db.commit()

    return VivaAnswerResult(
        questionId=payload.questionId,
        score=eval_dict["overall_score"],
        maxScore=5.0,
        evaluation=AnswerEvaluation(
            correctness=eval_dict["correctness"],
            completeness=eval_dict["completeness"],
            technicalDepth=eval_dict["technical_depth"],
            confidence=eval_dict["confidence"],
            overallScore=eval_dict["overall_score"],
        ),
        feedback=eval_dict["feedback"],
        strongPoints=eval_dict["strong_points"],
        weakPoints=eval_dict["weak_points"],
        conceptCovered=question.target_concept,
        nextQuestion=next_viva_q,
        sessionComplete=session.is_complete,
        kcsAfterAnswer=current_kcs,
    )


@router.get("/session/{session_id}/report", response_model=VivaReport)
def get_viva_report(session_id: str, current_user: CurrentUser, db: DB):
    """
    Returns the comprehensive research-grade Viva Assessment Report for a completed session.
    Includes overall score, Knowledge Coverage Score (KCS), dimensional metrics, gap analysis,
    and personalized learning recommendations.
    """
    session = db.query(VivaSession).filter(VivaSession.id == uuid.UUID(session_id)).first()
    if not session:
        raise HTTPException(status_code=404, detail="Viva session not found")

    if not session.is_complete or not session.report:
        # If not complete, compute transient report preview
        pool = decode_question_pool(session.questions)
        answer_records = decode_answer_records(session.answers)
        total_concepts = len({q.target_concept for q in pool})
        kcs = kcs_calculator.compute(answer_records, total_concepts)
        report_dict = viva_report_gen.generate(
            session_id=str(session.id),
            project_id=str(session.project_id),
            project_title=session.project.title if session.project else "Project Viva",
            answer_records=answer_records,
            pool=pool,
            difficulty_progression=session.difficulty_progression or [session.current_difficulty],
            kcs=kcs,
        )
        return VivaReport(**report_dict)

    return VivaReport(**session.report)


@router.get("/session/{session_id}/status", response_model=VivaSessionStatus)
def get_viva_session_status(session_id: str, current_user: CurrentUser, db: DB):
    """
    Polls the current status of an active or completed viva session.
    """
    session = db.query(VivaSession).filter(VivaSession.id == uuid.UUID(session_id)).first()
    if not session:
        raise HTTPException(status_code=404, detail="Viva session not found")

    pool = decode_question_pool(session.questions)
    answer_records = decode_answer_records(session.answers)
    total_concepts = len({q.target_concept for q in pool})
    current_kcs = session.kcs or kcs_calculator.compute(answer_records, total_concepts)
    
    progress = min(100.0, round((current_kcs / (KCS_COMPLETION_THRESHOLD * 100)) * 100, 1)) if KCS_COMPLETION_THRESHOLD > 0 else 100.0

    return VivaSessionStatus(
        sessionId=str(session.id),
        projectId=str(session.project_id),
        isComplete=session.is_complete,
        currentDifficulty=session.current_difficulty,
        questionsAnswered=len(answer_records),
        currentKcs=current_kcs,
        progressPct=progress,
    )
