from argparse import ArgumentParser
from typing import Any, Dict, List, Optional


def _extend_help_text(
    message: str, defaults: List[str], suffix: Optional[str] = None
) -> str:
    if not defaults:
        return message
    defaults = sorted(defaults)
    text = message + " in addition to "
    if len(defaults) >= 2 and suffix is not None:
        text += '"' + '", "'.join(defaults) + '", and ' + suffix
    elif len(defaults) > 2:
        text += '"' + '", "'.join(defaults[:-1]) + '", and "' + defaults[-1] + '"'
    elif len(defaults) == 2:
        text += f'"{defaults[0]}" and "{defaults[1]}"'
    elif suffix is not None:
        text += '"' + defaults[0] + '" and ' + suffix
    else:
        text += '"' + defaults[0] + '"'
    return text


def _process_positional(
    parser: ArgumentParser, args: List[Dict[str, Dict[str, Any]]]
) -> None:
    for arg in args:
        name = list(arg.keys())[0]
        params = list(arg.values())[0]
        params = params.copy()
        params.pop("postprocess", None)
        parser.add_argument(name.replace("_", "-"), **params)
        return None


def _get_order(args: Dict[str, Dict[str, Any]]) -> List[str]:
    with_sh = []
    min_sh = []
    without_sh = []
    for name, params in args.items():
        shorthands = params.get("shorthands", [])
        if shorthands:
            with_sh.append(name)
            min_sh.append(min(shorthands))
        else:
            without_sh.append(name)
    return [name for _, name in sorted(zip(min_sh, with_sh))] + sorted(without_sh)


def _process_optional(parser: ArgumentParser, args: Dict[str, Dict[str, Any]]) -> None:
    for name in _get_order(args=args):
        params = args[name].copy()
        shorthands = [f"-{shorthand}" for shorthand in params.pop("shorthands", [])]
        names_flags = sorted(shorthands) + [f"--{name.replace('_', '-')}"]
        try:
            if params["action"] == "extend":
                params["help"] = _extend_help_text(
                    message=params["help"],
                    defaults=params["default"],
                    suffix=params.pop("help_suffix", None),
                )
        except KeyError:
            pass
        params.pop("postprocess", None)
        parser.add_argument(*names_flags, **params)
    return None


def _postprocess(
    args: Dict[str, Any], params: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    for name, value in args.items():
        for func in params[name].get("postprocess", []):
            value = func(value)
        args[name] = value
    return args


def parse_arguments(
    description: str,
    positional: List[Dict[str, Dict[str, Any]]],
    optional: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    parser = ArgumentParser(description=description)
    _process_positional(parser=parser, args=positional)
    _process_optional(parser=parser, args=optional)
    return _postprocess(
        args=vars(parser.parse_args()),
        params=(
            {list(arg.keys())[0]: list(arg.values())[0] for arg in positional}
            | optional
        ),
    )
