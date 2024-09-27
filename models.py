import uuid
from typing import List, Union

# Define the Player class
class Player:
    def __init__(self, id: str, score: int = 0):
        self.id = id
        self.score = score

# Define the Log class
class Log:
    def __init__(self, player: str, move: str):
        self.player = player
        self.move = move

# Define the InitDataDTO class
class InitDataDTO:
    def __init__(self, id: str, players: List[Player], log: List[str], type: str, self_id: str):
        self.id = id
        self.players = players
        self.log = log
        self.type = type
        self.self = self_id

# Define the RoundDataDTO class
class RoundDataDTO:
    def __init__(self, id: str, players: List[Player], word: str, guessed: List[str], log: List[Log], type: str, self_id: str):
        self.id = id
        self.players = players
        self.word = word
        self.guessed = guessed
        self.log = log
        self.type = type
        self.self = self_id

# Define the ResultDataDTO class
class ResultDataDTO:
    def __init__(self, id: str, players: List[Player], word: str, guessed: List[str], log: List[Log], type: str, self_id: str):
        self.id = id
        self.players = players
        self.word = word
        self.guessed = guessed
        self.log = log
        self.type = type
        self.self = self_id

# Define the factory class
class DataDTOFactory:
    @staticmethod
    def create_dto(data_type: str, players: List[Player], log: Union[List[str], List[Log]], self_id: str, word: str = None, guessed: List[str] = None):
        dto_id = str(uuid.uuid4())  # Generate a unique id
        
        if data_type == "INIT":
            return InitDataDTO(id=dto_id, players=players, log=log, type=data_type, self_id=self_id)
        
        elif data_type == "ROUND":
            if word is None or guessed is None:
                raise ValueError("Word and guessed list must be provided for ROUND type")
            return RoundDataDTO(id=dto_id, players=players, word=word, guessed=guessed, log=log, type=data_type, self_id=self_id)
        
        elif data_type == "RESULT":
            if word is None or guessed is None:
                raise ValueError("Word and guessed list must be provided for RESULT type")
            return ResultDataDTO(id=dto_id, players=players, word=word, guessed=guessed, log=log, type=data_type, self_id=self_id)
        
        else:
            raise ValueError(f"Unknown data type: {data_type}")