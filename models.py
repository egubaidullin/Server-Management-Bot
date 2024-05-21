from dataclasses import dataclass

@dataclass
class Server:
    name: str
    ip: str
    port: int
    login: str
    password: str
