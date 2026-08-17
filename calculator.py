import ast
import logging
import math
import operator
import re
from typing import Union, Optional

logger = logging.getLogger(__name__)

class Calculator:
    """Safe mathematical expression calculator"""
    
    def __init__(self):
        self.max_length = 1000
        self.max_result = 1e100
        
        # Allowed operators and functions
        self.allowed_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        
        # Allowed node types
        self.allowed_nodes = (
            ast.Expression,
            ast.Constant,
            ast.BinOp,
            ast.UnaryOp,
            ast.Name,
            ast.Load,
        )
        
        # Allowed functions
        self.allowed_functions = {
            'abs': abs,
            'round': round,
            'min': min,
            'max': max,
            'sum': sum,
        }
    
    def calculate(self, expression: str) -> Union[int, float]:
        """Calculate mathematical expression safely"""
        
        # Check length
        if len(expression) > self.max_length:
            raise ValueError("Expression too long")
        
        # Clean expression
        cleaned = self._clean_expression(expression)
        
        # Parse and evaluate
        try:
            tree = ast.parse(cleaned, mode='eval')
            result = self._evaluate(tree.body)
            
            # Check result bounds
            if isinstance(result, (int, float)):
                if abs(result) > self.max_result:
                    raise ValueError("Result too large")
            
            # Format result
            if isinstance(result, float):
                if result.is_integer():
                    return int(result)
                # Round to avoid floating point issues
                return round(result, 10)
            return result
            
        except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError) as e:
            raise ValueError(f"Invalid expression: {e}")
        except Exception as e:
            logger.warning(f"Calculator error for expression '{expression}': {e}")
            raise ValueError("Invalid expression")
    
    def _clean_expression(self, expression: str) -> str:
        """Clean and normalize expression"""
        # Replace Unicode operators
        expression = expression.replace('×', '*')
        expression = expression.replace('÷', '/')
        expression = expression.replace('^', '**')
        
        # Handle percentage
        expression = self._handle_percentage(expression)
        
        # Replace common math functions
        expression = expression.replace('√', 'math.sqrt')
        expression = expression.replace('π', 'math.pi')
        expression = expression.replace('e', 'math.e')
        
        return expression
    
    def _handle_percentage(self, expression: str) -> str:
        """Handle percentage calculations"""
        # Simple percentage: number%
        def replace_simple_percent(match):
            num = match.group(1)
            return f"({num}/100)"
        
        # Complex percentage: number1% + number2%, etc.
        def replace_complex_percent(match):
            expr = match.group(0)
            # Parse the expression and handle percentage
            # For simplicity, we convert number% to (number/100)
            return re.sub(r'(\d+\.?\d*)%', r'(\1/100)', expr)
        
        # Handle cases like 100%*500, 10%+20%
        expression = re.sub(r'(\d+\.?\d*)%', r'(\1/100)', expression)
        
        return expression
    
    def _evaluate(self, node) -> Union[int, float]:
        """Evaluate AST node safely"""
        
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, bool, str)):
                return node.value
            raise ValueError(f"Unsupported constant: {type(node.value)}")
        
        elif isinstance(node, ast.BinOp):
            left = self._evaluate(node.left)
            right = self._evaluate(node.right)
            
            op_type = type(node.op)
            
            # Division by zero check
            if op_type == ast.Div and right == 0:
                raise ZeroDivisionError("Division by zero")
            
            op_func = self.allowed_operators.get(op_type)
            if not op_func:
                raise ValueError(f"Unsupported operator: {op_type}")
            
            try:
                result = op_func(left, right)
                return result
            except Exception as e:
                raise ValueError(f"Operation error: {e}")
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._evaluate(node.operand)
            op_type = type(node.op)
            op_func = self.allowed_operators.get(op_type)
            if not op_func:
                raise ValueError(f"Unsupported unary operator: {op_type}")
            return op_func(operand)
        
        elif isinstance(node, ast.Name):
            # Check if it's an allowed function or constant
            if node.id in self.allowed_functions:
                return self.allowed_functions[node.id]
            if node.id in ['math']:
                return math
            raise ValueError(f"Unknown name: {node.id}")
        
        elif isinstance(node, ast.Call):
            func = self._evaluate(node.func)
            args = [self._evaluate(arg) for arg in node.args]
            
            if not callable(func):
                raise ValueError(f"Not callable: {func}")
            
            # Check if it's a math function
            if func in self.allowed_functions.values():
                try:
                    return func(*args)
                except Exception as e:
                    raise ValueError(f"Function error: {e}")
            else:
                # Check if it's a math module function
                if hasattr(math, func.__name__) and callable(getattr(math, func.__name__)):
                    try:
                        return func(*args)
                    except Exception as e:
                        raise ValueError(f"Math function error: {e}")
                raise ValueError(f"Function not allowed: {func}")
        
        elif isinstance(node, ast.Attribute):
            # Allow math.xxx
            if isinstance(node.value, ast.Name) and node.value.id == 'math':
                attr_name = node.attr
                if hasattr(math, attr_name):
                    return getattr(math, attr_name)
                raise ValueError(f"Unknown math attribute: {attr_name}")
            raise ValueError(f"Attribute access not allowed: {node.attr}")
        
        else:
            raise ValueError(f"Unsupported AST node: {type(node)}")
