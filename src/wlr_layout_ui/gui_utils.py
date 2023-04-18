def get_square_shape(position, size=50, orientation="t"):
    half_size = size // 2
    return [
        (position[0] - half_size, position[1] - half_size),
        (position[0] + half_size, position[1] - half_size),
        (position[0] + half_size, position[1] + half_size),
        (position[0] - half_size, position[1] + half_size),
    ]


def get_arrow_shape(position, size=50, orientation="t"):
    x, y = position
    half_size = size // 2

    if orientation == "r":
        points = [
            (x - half_size, y - half_size),
            (x + half_size, y),
            (x - half_size, y + half_size),
        ]
    elif orientation == "l":
        points = [
            (x + half_size, y - half_size),
            (x - half_size, y),
            (x + half_size, y + half_size),
        ]
    elif orientation == "t":
        points = [
            (x, y - half_size),
            (x - half_size, y + half_size),
            (x + half_size, y + half_size),
        ]
    elif orientation == "b":
        points = [
            (x - half_size, y - half_size),
            (x + half_size, y - half_size),
            (x, y + half_size),
        ]
    else:
        raise ValueError(f"Invalid orientation '{orientation}'.")
    return points
