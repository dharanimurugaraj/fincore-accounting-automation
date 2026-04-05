"""
Dynamic Formula Loader.
Fetches expressions from the database and provides a safe evaluation context.
"""

from app.core.database import execute_query

class FormulaLoader:
    def __init__(self, org_id: str):
        self.org_id = org_id
        self.formulas = {}
        self.load_all()

    def load_all(self):
        """Cache all active formulas for the organisation."""
        rows = execute_query(
            'SELECT name, expression, parameters FROM "FormulaConfiguration" WHERE "orgId" = %s AND "isActive" = TRUE',
            (self.org_id,)
        )
        for r in rows:
            self.formulas[r["name"]] = {
                "expression": r["expression"],
                "parameters": r["parameters"] if isinstance(r["parameters"], dict) else {}
            }

    def evaluate(self, name: str, context: dict) -> float:
        """Evaluate a formula by name with given context variables."""
        if name not in self.formulas:
            raise ValueError(f"Formula '{name}' not found for org {self.org_id}")

        formula_data = self.formulas[name]
        expression = formula_data["expression"]
        
        # Merge formula-defined parameters with call-time context
        full_context = {**formula_data["parameters"], **context}
        
        try:
            # We use a restricted eval for safety
            # In production, consider a real DSL parser like 'simpleeval'
            result = eval(expression, {"__builtins__": {}}, full_context)
            return float(result)
        except Exception as e:
            print(f"Error evaluating formula {name}: {e}")
            return 0.0

def get_formula_engine(org_id: str) -> FormulaLoader:
    return FormulaLoader(org_id)
