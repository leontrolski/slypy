from typing import Literal


class SlyPyError(RuntimeError): ...


ErrorKind = Literal["unresolved-reference"]
