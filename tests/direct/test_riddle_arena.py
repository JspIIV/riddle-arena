import json


def _mock_riddle(direct_vm, riddle_text="What has keys but no locks?", answer="a piano"):
    direct_vm.mock_llm(
        r".*Generate a short, clever riddle.*",
        json.dumps({"riddle_text": riddle_text, "answer": answer}),
    )


def _mock_answer_check(direct_vm, correct: bool):
    direct_vm.mock_llm(
        r".*judging a riddle game answer.*",
        json.dumps({"correct": correct}),
    )


def test_create_riddle_stores_riddle_and_answer(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/riddle_arena.py")
    direct_vm.sender = direct_alice
    _mock_riddle(direct_vm)

    contract.create_riddle("music", "medium")

    riddle = json.loads(contract.get_riddle("0"))
    assert riddle["topic"] == "music"
    assert riddle["difficulty"] == "medium"
    assert riddle["riddle_text"] == "What has keys but no locks?"
    assert riddle["answer"] == "a piano"
    assert riddle["solved"] is False
    assert riddle["solved_by"] is None
    assert int(contract.get_total_riddle_count()) == 1


def test_multiple_riddles_get_sequential_ids(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/riddle_arena.py")
    direct_vm.sender = direct_alice
    _mock_riddle(direct_vm, "riddle one", "answer one")

    contract.create_riddle("science", "easy")
    contract.create_riddle("science", "easy")

    assert int(contract.get_total_riddle_count()) == 2
    assert json.loads(contract.get_riddle("0"))["id"] == "0"
    assert json.loads(contract.get_riddle("1"))["id"] == "1"


def test_submit_correct_answer_marks_solved_and_awards_points(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/riddle_arena.py")
    direct_vm.sender = direct_alice
    _mock_riddle(direct_vm)
    contract.create_riddle("music", "medium")

    _mock_answer_check(direct_vm, correct=True)
    contract.submit_answer("0", "bob", "piano")

    riddle = json.loads(contract.get_riddle("0"))
    assert riddle["solved"] is True
    assert riddle["solved_by"] == "bob"

    player = json.loads(contract.get_player("bob"))
    assert player["score"] == 10
    assert player["solved_count"] == 1
    assert player["attempts"] == 1


def test_submit_wrong_answer_does_not_solve_or_award_points(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/riddle_arena.py")
    direct_vm.sender = direct_alice
    _mock_riddle(direct_vm)
    contract.create_riddle("music", "medium")

    _mock_answer_check(direct_vm, correct=False)
    contract.submit_answer("0", "bob", "a guitar")

    riddle = json.loads(contract.get_riddle("0"))
    assert riddle["solved"] is False
    assert riddle["solved_by"] is None

    player = json.loads(contract.get_player("bob"))
    assert player["score"] == 0
    assert player["solved_count"] == 0
    assert player["attempts"] == 1


def test_cannot_answer_already_solved_riddle(
    direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie
):
    contract = direct_deploy("contracts/riddle_arena.py")
    direct_vm.sender = direct_alice
    _mock_riddle(direct_vm)
    contract.create_riddle("music", "medium")

    _mock_answer_check(direct_vm, correct=True)
    contract.submit_answer("0", "bob", "piano")

    with direct_vm.expect_revert("Riddle already solved"):
        contract.submit_answer("0", "charlie", "piano")


def test_submit_answer_to_missing_riddle_reverts(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/riddle_arena.py")
    direct_vm.sender = direct_alice

    with direct_vm.expect_revert("Riddle not found"):
        contract.submit_answer("999", "alice", "anything")


def test_get_player_defaults_for_unknown_player(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/riddle_arena.py")
    direct_vm.sender = direct_alice

    player = json.loads(contract.get_player("nobody"))
    assert player["score"] == 0
    assert player["solved_count"] == 0
    assert player["attempts"] == 0


def test_player_accumulates_score_across_multiple_solved_riddles(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/riddle_arena.py")
    direct_vm.sender = direct_alice
    _mock_riddle(direct_vm, "riddle one", "answer one")
    contract.create_riddle("science", "easy")
    _mock_riddle(direct_vm, "riddle two", "answer two")
    contract.create_riddle("science", "easy")

    _mock_answer_check(direct_vm, correct=True)
    contract.submit_answer("0", "bob", "answer one")
    contract.submit_answer("1", "bob", "answer two")

    player = json.loads(contract.get_player("bob"))
    assert player["score"] == 20
    assert player["solved_count"] == 2
    assert player["attempts"] == 2


def test_get_all_riddles_returns_every_riddle(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/riddle_arena.py")
    direct_vm.sender = direct_alice
    _mock_riddle(direct_vm, "riddle one", "answer one")
    contract.create_riddle("science", "easy")
    _mock_riddle(direct_vm, "riddle two", "answer two")
    contract.create_riddle("history", "hard")

    all_riddles = json.loads(contract.get_all_riddles())
    assert len(all_riddles) == 2
    assert all_riddles["0"]["topic"] == "science"
    assert all_riddles["1"]["topic"] == "history"
