# research/ — Archivo (NO es parte del bot DCA)

Esto es el laboratorio de las estrategias que probamos **antes** de decidir el DCA.
**No corre en producción** y el bot DCA no depende de nada de acá.

## Qué hay

- `backtest_momentum.py`, `backtest_meanrev.py`, `signal.py` — estrategias activas.
- `walk_forward.py`, `walk_forward_mr.py` — validación out-of-sample (multi-fold).
- `run_backtest.py`, `make_report.py`, `reporting.py` — backtests y reportes HTML.

## Por qué se conserva

Las dos estrategias **fallaron** la validación honesta (ver README principal):
momentum overfitteó, mean-reversion no tuvo edge (0/4 folds). Pero el **harness
de walk-forward** es valioso: es la herramienta que usa la regla de oro del proyecto:

> Un bot solo gradúa a plata real si **le gana al DCA en validación OOS honesta**.

El holdout 2025-06 → 2026-06 sigue **intacto** para esa prueba futura.

## ¿No lo querés?

Si preferís un repo DCA-only, se puede borrar entero sin afectar el bot:
`rm -rf research/`. Queda en el historial de git por si lo necesitás después.
