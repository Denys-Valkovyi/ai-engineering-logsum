The messiest function is summarise. The main issues:
- Trailing semicolon on line 40
- Group state stored as a magic-index list [0, None, None] (indices 0/1/2 with a comment explaining what they mean)
- Manual if key not in groups guard instead of setdefault

The removed pattern is the positional list [0, None, None] used to store count, first_seen, last_seen accessed by index (groups[key][0], [1], [2]). Replaced it with a named dict ({"count": 0, "first_seen": None, "last_seen": None}).

Nothing was lost behaviourally, but the old structure was implicit you had to know position 0 meant count. Your decision: keep removed (the named dict is clearer and matches no spec contract).