from functools import reduce

def power_mean(order):
    match order:
        case 0:         return lambda vlist: reduce(lambda x, y: x*y, vlist)**(1/len(vlist))
        case '+inf':    return lambda vlist: max(vlist)
        case '-inf':    return lambda vlist: min(vlist)
        case _:         return lambda vlist: ((1/len(vlist))*sum(map(lambda x: x**order, vlist)))**(1/order)

def quasi_arithmetic_mean(func, inverse_func):
    return lambda vlist: inverse_func((1/len(vlist))*sum(map(lambda x: func(x), vlist)))

    