# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json

POINTS_PER_CORRECT_ANSWER = 10


class RiddleArena(gl.Contract):
    riddles: TreeMap[str, str]
    riddle_count: bigint
    players: TreeMap[str, str]

    def __init__(self) -> None:
        self.riddle_count = bigint(0)

    @gl.public.write
    def create_riddle(self, topic: str, difficulty: str) -> None:
        def parse_riddle(raw: str) -> dict:
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                raw = raw[start:end]
            parsed = json.loads(raw)
            riddle_text = str(parsed.get("riddle_text", "")).strip()
            answer = str(parsed.get("answer", "")).strip().lower()
            if not riddle_text or not answer:
                raise gl.vm.UserError("[LLM_ERROR] Missing riddle_text or answer")
            return {"riddle_text": riddle_text, "answer": answer}

        def leader_fn() -> dict:
            task = (
                "Generate a short, clever riddle for a game.\n"
                "TOPIC: " + topic + "\n"
                "DIFFICULTY: " + difficulty + "\n\n"
                "Return ONLY a JSON object:\n"
                "{\"riddle_text\": \"...\", \"answer\": \"one or two words\"}\n\n"
                "Rules:\n"
                "- riddle_text: the riddle itself, 1-3 sentences, do not reveal the answer\n"
                "- answer: the single correct answer, lowercase, one or two words\n"
                "Return ONLY the JSON, no other text."
            )
            raw = gl.nondet.exec_prompt(task)
            return parse_riddle(raw)

        def validator_fn(leaders_res: gl.vm.Result) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            leader_data = leaders_res.calldata
            riddle_text = leader_data.get("riddle_text", "")
            answer = leader_data.get("answer", "")
            if not riddle_text or not answer:
                return False

            task = (
                "You are judging whether a riddle is internally consistent and fair.\n\n"
                "RIDDLE: " + riddle_text + "\n"
                "CLAIMED ANSWER: " + answer + "\n\n"
                "Does this riddle clue the claimed answer in a fair, solvable way, and does the\n"
                "riddle avoid directly stating the answer?\n"
                "Return ONLY a JSON object:\n"
                "{\"valid\": true}\n\n"
                "Return ONLY the JSON, no other text."
            )
            raw = gl.nondet.exec_prompt(task)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                raw = raw[start:end]
            parsed = json.loads(raw)
            return bool(parsed.get("valid", False))

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        riddle_id = str(int(self.riddle_count))
        self.riddles[riddle_id] = json.dumps({
            "id": riddle_id,
            "topic": topic,
            "difficulty": difficulty,
            "riddle_text": result["riddle_text"],
            "answer": result["answer"],
            "solved": False,
            "solved_by": None,
        })
        self.riddle_count = bigint(int(self.riddle_count) + 1)

    def _get_or_init_player(self, player: str) -> dict:
        raw = self.players.get(player, None)
        if raw is None:
            return {"player": player, "score": 0, "solved_count": 0, "attempts": 0}
        return json.loads(raw)

    @gl.public.write
    def submit_answer(self, riddle_id: str, player: str, answer: str) -> None:
        riddle_raw = self.riddles.get(riddle_id, None)
        if riddle_raw is None:
            raise gl.vm.UserError("[EXPECTED] Riddle not found")
        riddle = json.loads(riddle_raw)
        if riddle["solved"]:
            raise gl.vm.UserError("[EXPECTED] Riddle already solved")

        riddle_text = riddle["riddle_text"]
        correct_answer = riddle["answer"]

        def check() -> str:
            task = (
                "You are judging a riddle game answer.\n\n"
                "RIDDLE: " + riddle_text + "\n"
                "CORRECT ANSWER: " + correct_answer + "\n"
                "PLAYER'S SUBMITTED ANSWER: " + answer + "\n\n"
                "Decide if the player's answer is semantically the same as the correct answer,\n"
                "allowing for synonyms, plurals, and minor spelling variation.\n"
                "Return ONLY a JSON object:\n"
                "{\"correct\": true}\n\n"
                "Return ONLY the JSON, no other text."
            )
            raw = gl.nondet.exec_prompt(task)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                raw = raw[start:end]
            parsed = json.loads(raw)
            return json.dumps({"correct": bool(parsed.get("correct", False))})

        result_str = gl.eq_principle.prompt_comparative(
            check,
            principle="The correct field must match exactly between validators.",
        )
        result = json.loads(result_str)
        is_correct = result["correct"]

        player_data = self._get_or_init_player(player)
        player_data["attempts"] = int(player_data["attempts"]) + 1

        if is_correct:
            riddle["solved"] = True
            riddle["solved_by"] = player
            self.riddles[riddle_id] = json.dumps(riddle)
            player_data["score"] = int(player_data["score"]) + POINTS_PER_CORRECT_ANSWER
            player_data["solved_count"] = int(player_data["solved_count"]) + 1

        self.players[player] = json.dumps(player_data)

    @gl.public.view
    def get_riddle(self, riddle_id: str) -> str:
        data = self.riddles.get(riddle_id, None)
        if data is None:
            return json.dumps({"error": "Riddle not found"})
        return data

    @gl.public.view
    def get_all_riddles(self) -> str:
        all_riddles = {}
        for i in range(int(self.riddle_count)):
            rid = str(i)
            all_riddles[rid] = json.loads(self.riddles.get(rid, "{}"))
        return json.dumps(all_riddles)

    @gl.public.view
    def get_player(self, player: str) -> str:
        raw = self.players.get(player, None)
        if raw is None:
            return json.dumps({"player": player, "score": 0, "solved_count": 0, "attempts": 0})
        return raw

    @gl.public.view
    def get_total_riddle_count(self) -> bigint:
        return self.riddle_count
