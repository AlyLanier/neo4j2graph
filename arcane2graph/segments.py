class Segment:
    def __init__(self, start: float, end: float) -> None:
        if start >= end: raise Exception(f"those segments must be valid and contain more than one value, found [{start}, {end}]")
        self.set_start(start)
        self.set_end(end)

    def __contains__(self, item: float|Segment) -> bool:
        try:
            item = float(item)
            return self.get_start() <= item <= self.get_end()
        except:
            return self.get_start() <= item.get_start() and item.get_end() <= self.get_end()
            
    def __repr__(self) -> str:
        return f"S[{self.get_start()}, {self.get_end()}]S"

    def __eq__(self, other: Segment):
        return self.get_start() == other.get_start() and self.get_end() == other.get_end()

    def __hash__(self):
        return hash(tuple(sorted(self.__dict__.items())))

    def copy(self) -> Segment:
        return Segment(self.get_start(), self.get_end())

    def get_start(self) -> float:
        return self.start

    def get_end(self) -> float:
        return self.end

    def set_start(self, new_start: float) -> None:
        self.start = new_start

    def set_end(self, new_end: float) -> None:
        self.end = new_end

    def as_tuple(self) -> tuple[float, float]:
        return (self.get_start(), self.get_end())