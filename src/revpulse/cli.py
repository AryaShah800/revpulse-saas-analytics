"""Command-line interface for the complete local analytics workflow."""
import argparse
import json
from pathlib import Path
from .core import Config,root_default,current_run

def main():
    parser=argparse.ArgumentParser(description='RevPulse reproducible SaaS analytics')
    parser.add_argument('command',choices=['generate','ingest','validate','build','build-marts','export','train','score','all'])
    parser.add_argument('--workspace',type=Path,default=root_default())
    parser.add_argument('--config',type=Path)
    parser.add_argument('--accounts',type=int)
    parser.add_argument('--months',type=int)
    parser.add_argument('--seed',type=int)
    parser.add_argument('--start')
    parser.add_argument('--source',type=Path)
    args=parser.parse_args()
    try:
        config_file=args.config or args.workspace/'config/project.json'
        defaults=json.loads(config_file.read_text()) if config_file.exists() else {}
        cfg=Config(args.workspace.resolve(),args.seed if args.seed is not None else defaults.get('seed',42),args.accounts if args.accounts is not None else defaults.get('accounts',1000),args.start or defaults.get('start','2023-01-01'),args.months if args.months is not None else defaults.get('months',36))
        if args.command=='generate':
            from .generate import generate
            print(generate(cfg));return
        if args.command in ['ingest','validate']:
            from .generate import generate
            from .clean import clean
            import uuid
            output=cfg.root/'data/validation'/uuid.uuid4().hex
            clean(args.source or generate(cfg),output);print(output);return
        if args.command in ['build','build-marts','all']:
            from .pipeline import build
            run=build(cfg,args.source);print('Published:',run)
        else:run=current_run(cfg.root)
        if args.command in ['train','all']:
            from .analytics import analyze
            analyze(run,cfg.root)
            from .model import train
            train(run,cfg.root)
        if args.command=='score':
            from .model import score
            score(run,cfg.root)
        if args.command in ['export','all','score']:
            from .pipeline import export_current
            print('Dashboard exports:',export_current(cfg.root))
    except (ValueError,RuntimeError,FileNotFoundError) as e:parser.exit(1,f'RevPulse: {e}\n')

if __name__=='__main__':main()
