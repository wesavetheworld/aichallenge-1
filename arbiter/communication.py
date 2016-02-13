import sys
from itertools import chain

from arbiter import Game, Fort, March, unorder


def read_section(handle):
    header = handle.readline()
    section_length = int(header.split(' ')[0])
    return [handle.readline().rstrip() for i in range(section_length)]


def read_sections(handle, *parsers):
    for parser in parsers:
        for line in read_section(handle):
            parser(line)


def parse_fort(game, string):
    name, x, y, owner, garrison = string.split(' ')
    Fort(game, name, float(x), float(y), owner, int(garrison))


def parse_road(game, string):
    a, b = string.split(' ')
    game.forts[a].neighbours.add(game.forts[b])
    game.forts[b].neighbours.add(game.forts[a])


def parse_march(game, string):
    origin, target, owner, size, steps = string.split(' ')
    March(game, game.forts[origin], game.forts[target],
            owner, int(size), int(steps))


def read_game(handle):
    game = Game()
    read_sections(handle,
            lambda line: parse_fort(game, line),
            lambda line: parse_road(game, line),
            lambda line: parse_march(game, line))
    return game


def parse_command(self, string):
    origin, target, size = string.rstrip().split(' ')
    origin, target = self.game.forts[origin], self.game.forts[target]
    if origin and origin.owner == self.player:
        origin.dispatch(target, int(size))


def show_section(items, name, fun):
    header = "{} {}:".format(len(items), name)
    body = (fun(item) for item in items)
    return '\n'.join([header, *body])


def show_fort(fort):
    return "{} {} {} {} {}".format(
            fort.name, fort.x, fort.y, fort.owner, fort.garrison)


def show_road(road):
    return "{} {}".format(*road)


def show_march(march):
    return "{} {} {} {} {}".format(
            march.origin, march.target, march.owner,
            march.size, march.remaining_steps)


def show_visible(game, forts):
    visible_forts = set.union(*(fort.neighbours for fort in forts))
    roads = set(unorder((fort, n)) for fort in forts for n in fort.neighbours)
    marches = list(chain(*(game.roads[road].marches() for road in roads)))
    return '\n'.join([
        show_section(visible_forts, 'forts', show_fort),
        show_section(roads, 'roads', show_road),
        show_section(marches, 'marches', show_march)
        ])