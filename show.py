import ser

def show_instruction(insn):
    return insn.mnemonic + "\t" + insn.op_str

def get_name_for_address(parsed, offset):
    if offset in parsed['address-to-name']:
        return parsed['address-to-name'][offset]
    else:
        return "loc_" + str(offset)

def show_pretty(parsed, pointer):
    try:
        if pointer == None:
            return "None"
        elif pointer['type'] == 'static':
            name = get_name_for_address(parsed, pointer['value'])
            if name_is_library(name):
                name = name.split('_')[2]
            return demangle(name)
        elif pointer['type'] == 'dynamic':
            return "<index " + str(pointer['index']) + " in " + show_pretty(parsed, ser.deserialize(pointer['heap-segment'])) + "'s heap, tag " + str(pointer['tag']) + ">"
        elif pointer['type'] == 'argument':
            return demangle(pointer['stack-segment']) + "_arg_" + str(pointer['index'])
        elif pointer['type'] == 'case-argument':
            return pointer['value'] + "_case_input"
        elif pointer['type'] == 'unknown':
            return "!unknown!"
        else:
            return "<<unknown type in show_pretty: " + pointer['type'] + ">>"
    except:
        return ("<<Error in show_pretty, pointer = " + str(pointer) + ">>")

def show_pretty_nonptr(parsed, value, context):
    assert value['type'] == 'static'
    if context == 'unpackCString#':
        ret = '"'
        parsed_offset = parsed['rodata-offset'] + value['value']
        while parsed['binary'][parsed_offset] != 0:
            ret += chr(parsed['binary'][parsed_offset])
            parsed_offset += 1
        ret += '"'
        return ret
    else:
        return str(value['value'])

def show_pretty_interpretation(parsed, interp):
    return '\n'.join(render_pretty_interpretation(parsed, interp, False))

def render_pretty_interpretation(parsed, interp, wants_parens):
    if interp['type'] == 'apply':
        func = render_pretty_interpretation(parsed, interp['func'], False)
        args = []
        for arg, pat in zip(interp['args'], interp['pattern']):
            if pat == 'p':
                args.append(render_pretty_interpretation(parsed, arg, True))
            elif pat == 'n':
                if len(func) == 1:
                    context = func[0]
                else:
                    context = ""
                args.append([show_pretty_nonptr(parsed, arg, context)])
            else:
                assert False, "bad argument pattern"

        if len(func) > 1 or any(map(lambda arg: len(arg) > 1, args)):
            ret = func
            for arg in args:
                ret += map(lambda line: "    " + line, arg)
        else:
            ret = [func[0] + ''.join(map(lambda arg: " " + arg[0], args))]
    elif interp['type'] == 'case-default':
        scrutinee = render_pretty_interpretation(parsed, interp['scrutinee'], False)
        if len(scrutinee) > 1:
            ret = scrutinee
            ret += ["of"]
            ret[0] = "case " + ret[0]
        else:
            ret = ["case " + scrutinee[0] + " of"]

        arm = render_pretty_interpretation(parsed, interp['arm'], False)
        arm[0] = demangle(interp['bound-name']) + "_case_input@_DEFAULT -> " + arm[0]

        ret += map(lambda line: "    " + line, arm)
    elif interp['type'] == 'case-bool':
        scrutinee = render_pretty_interpretation(parsed, interp['scrutinee'], False)
        if len(scrutinee) > 1:
            ret = scrutinee
            ret += ["of"]
            ret[0] = "case " + ret[0]
        else:
            ret = ["case " + scrutinee[0] + " of"]
        arm_true = render_pretty_interpretation(parsed, interp['arm-true'], False)
        arm_false = render_pretty_interpretation(parsed, interp['arm-false'], False)

        arm_true[0] = "True -> " + arm_true[0]
        arm_true[-1] = arm_true[-1] + ","
        arm_false[0] = "False -> " + arm_false[0]

        ret += map(lambda line: "    " + line, arm_true)
        ret += map(lambda line: "    " + line, arm_false)
    else:
        return [show_pretty(parsed, interp)]

    if wants_parens:
        if len(ret) > 1:
            ret[0] = "(" + ret[0]
            ret.append(")")
        else:
            ret = ["(" + ret[0] + ")"]

    return ret

def demangle(ident):
    table = {'L': '(', 'R': ')', 'M': '[', 'N': ']', 'C': ':', 'Z': 'Z', 'a': '&', 'b': '|', 'c': '^', 'd': '$', 'e': '=', 'g': '>', 'h': '#', 'i': '.', 'l': '<', 'm': '-', 'n': '!', 'p': '+', 'q': '\'', 'r': '\\', 's': '/', 't': '*', 'v': '%', 'z': 'z'}
    out = ""
    i = 0
    while i < len(ident):
        if ident[i] == 'z' or ident[i] == 'Z':
            if ident[i+1] in table:
                out += table[ident[i+1]]
                i += 2
                continue
        out += ident[i]
        i += 1
    return out

def name_is_library(name):
    parts = name.split('_')
    return len(parts) >= 4 and (parts[-1] == 'info' or parts[-1] == 'closure')