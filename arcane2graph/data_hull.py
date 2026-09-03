from option_hull import HullByParts
from segments import Segment
import numpy as np


class ChartDataMaker:

    def __init__(self, options, hull_range, reference_function = None, reference_primitive = None):
        self.values_to_occurrences = options
        print(hull_range)
        print(options)
        self.hull = HullByParts([(1./occ, value) for value, occ in options.items()], Segment(*hull_range) if hull_range is not None else None, reference_function, reference_primitive)

    def get_hull(self):
        return self.hull

    def get_options(self):
        return self.values_to_occurrences

    def get_function(self):
        return self.get_hull().get_reference_function()

    def get_primitive(self):
        return self.get_hull().get_primitive()

    def set_function(self, func):
        self.get_hull().set_reference_function(func)

    def set_primitive(self, func):
        self.get_hull().set_primitive(func)

    def add_option(self, value, occurrences):
        options = self.get_options()
        if value in options:
            options[value] += occurrences
        else:
            options[value] = occurrences

        self.get_hull().add_subfunction((1./occurrences, value))

    @staticmethod
    def normalize_score(liste):
        if liste.size == 0: return
        min_value = min(liste)
        max_value = max(liste)

        return lambda l : (l - min_value)/(max_value - min_value)

    def generate_data(self, nbpoints, with_score=False):
        x = np.linspace(*self.get_hull().get_range().as_tuple(), nbpoints)
        y = self.get_hull()(x)

        if with_score:
            max_height = max(y)
            options = self.get_options()

            #fig = plotille.Figure()
            
            x_score = []
            score = []
            for v in x: 
                if v not in options:
                    x_score.append(v)
                    score.append(self.get_hull().score_of_new_curb_test((1., v)))
            score = np.array(score)

            x_taken_values_score = []
            taken_values_score = []
            for v in options:
                x_taken_values_score.append(v)
                taken_values_score.append(self.get_hull().score_of_new_curb_test((1./(options[v]+1), v)))
            

            taken_values_score = np.array(taken_values_score)
            x_taken_values_score = np.array(x_taken_values_score)

            norm = ChartDataMaker.normalize_score(np.concatenate((score, taken_values_score), axis=0))
            score = norm(score)*max_height
            taken_values_score = norm(taken_values_score)*max_height

        return x, y, x_score, score, x_taken_values_score, taken_values_score

if __name__ == '__main__':
    option = {
                .1: 13,
                2.5: 37,
                4.45: 2,
                4.7: 3,
                6: 17,
                7.5: 5,
                7.9: 6,
                8.33: 2,
                10.55: 35
            }
    sign = lambda x: 1. if x >= 0 else -1.
    power = lambda n: (lambda x: abs(x)**n, lambda a: (lambda x: sign(x)*a**n * abs(x)**(n+1)/(n+1)))
    distance_function = power(2)

    data_maker = ChartDataMaker(option, (0., 11.), *distance_function)
    x, y, x_score, score, x_of_values, score_of_values = data_maker.generate_data(100, True)
    #print(x, y, score, x_of_values, score_of_values)
