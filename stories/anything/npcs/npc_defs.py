

class StationaryMob(LivingNpc):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str):
        super(StationaryMob, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, age=age, personality=personality, occupation='')

    @call_periodically(15, 30)
    def do_idle_action(self, ctx: Context) -> None:
        pass
    # do nothing if player not present

class RoamingMob(StationaryMob):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str):
        super(StationaryMob, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, age=age, personality=personality, occupation='')

    @call_periodically(20, 40)
    def do_random_move(self, ctx: Context) -> None:
        direction = self.select_random_move()
        if direction:
            self.move(direction.target, self, direction_names=direction.names)
