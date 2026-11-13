"""Model Risk Factory - command line.

  python main.py setup                         # build data split + legacy model estate
  python main.py status                        # show every stage and its review status
  python main.py run discover                  # run one stage (needs previous stage approved)
  python main.py approve discover --reviewer "Jane Doe" --comment "Inventory checked"
  python main.py reject  discover --reviewer "Jane Doe" --comment "Missing model"
  python main.py run monitor --scenario drift --severity 0.6
  python main.py run-all --reviewer "Jane Doe"            # interactive approvals
  python main.py run-all --reviewer "CI" --auto-approve   # testing only, logged as automated
  python main.py reset                         # clear stage statuses (outputs are kept)
"""
import argparse
import json
import sys

from core import config, pipeline, state


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Model Risk Factory")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    sub.add_parser("status")
    sub.add_parser("reset")
    r = sub.add_parser("run")
    r.add_argument("stage", choices=config.PIPELINE_STAGES)
    r.add_argument("--actor")
    r.add_argument("--scenario", default="drift", choices=["stable", "drift"])
    r.add_argument("--severity", type=float, default=0.6)
    for name in ("approve", "reject"):
        a = sub.add_parser(name)
        a.add_argument("stage", choices=config.PIPELINE_STAGES)
        a.add_argument("--reviewer", required=True)
        a.add_argument("--comment", default="")
    ra = sub.add_parser("run-all")
    ra.add_argument("--reviewer", required=True)
    ra.add_argument("--auto-approve", action="store_true")
    args = p.parse_args(argv)

    if args.cmd == "setup":
        pipeline.setup()
    elif args.cmd == "status":
        st = state.load()
        for s in config.PIPELINE_STAGES:
            info = st["stages"][s]
            rev = info.get("review", {})
            print(f"{s:<10} {info['status']:<12} {rev.get('reviewer', '')} {rev.get('comment', '')}")
    elif args.cmd == "reset":
        state.reset()
        print("Pipeline state reset.")
    elif args.cmd == "run":
        kwargs = {"scenario": args.scenario, "severity": args.severity} if args.stage == "monitor" else {}
        try:
            print(json.dumps(pipeline.run_stage(args.stage, actor=args.actor, **kwargs), indent=2, default=float))
        except PermissionError as e:
            print(f"BLOCKED: {e}")
            return 1
    elif args.cmd in ("approve", "reject"):
        state.record_review(args.stage, "approved" if args.cmd == "approve" else "rejected",
                            args.reviewer, args.comment)
        print(f"{args.stage}: {args.cmd}d by {args.reviewer}")
    elif args.cmd == "run-all":
        pipeline.run_all(args.reviewer, args.auto_approve)
    return 0


if __name__ == "__main__":
    sys.exit(main())
