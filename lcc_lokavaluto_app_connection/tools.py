def status(reqs):
    """Return 'todo', 'done' or 'ongoing' depending if all reqs are
    not done, all done or some done.

    reqs are boolean, True to say they are done, False to say they are not done.

    Reqs is an iterable:

        >>> status(iter([True, True, True]))
        'done'
        >>> status(iter([True, True, False]))
        'ongoing'
        >>> status(iter([False, False, False]))
        'todo'
        >>> status(iter([]))
        'done'

    """
    one = {False: False, True: False}
    for r in reqs:
        if one[r]:
            continue
        one[r] = True
        if one[not r]:
            ## then we have both at least one done and one not done
            return "ongoing"
    return "todo" if one[False] else "done"
