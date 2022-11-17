#!/usr/bin/env python3

import typing as t

from GuaLexer import GuaLexer
from GuaParser import GuaParser
from GuaVisitor import GuaVisitor


def log(*args):
    print(*args, flush=True)


def string_with_space(num: int, string: str) -> str:
    return num * '    ' + string


def type_string_add(a: str, b: str) -> str:
    if a == 'int':
        if b == 'int':
            return 'int'
        else:
            raise ValueError(f'type_string_add 1')
    elif a == 'float':
        if b == 'float':
            return 'float'
        else:
            raise ValueError(f'type_string_add 2')
    elif a == 'string':
        if b == 'string':
            return 'string'
        else:
            raise ValueError(f'type_string_add 3')
    elif a == 'bool':
        if b == 'bool':
            return 'bool'
        else:
            raise ValueError(f'type_string_add 4')
    else:
        raise ValueError(f'type_string_add 5')


def output_type_string(type_string: str) -> str:
    return type_string\
        .replace('int', 'int64_t')\
        .replace('float', 'float_t')\
        .replace('string', 'NSString *')


def output_container_type_string(type_string: str) -> str:
    return type_string[type_string.index(']') + 1:]


def container_value_type_string(type_string: str) -> str:
    return type_string[type_string.index(']') + 1:]


def class_type_string(type_string: str) -> str:
    if type_string[0] == '*':
        return type_string[1:]
    return type_string


def method_name(format_string: str) -> str:
    return format_string[:format_string.index('(')]


class EvalVisitor(GuaVisitor):
    def __init__(self):
        self.num = -1

        self.class_field_map = {}
        self.class_method_map = {}
        self.function_map = {}

        self.in_new_method = False
        self.current_class = ''

        self.blocks = []
        self.temp_block = {}

        self.clain_item_type_string = ''

    def add_block(self):
        self.blocks.append({})

    def del_block(self):
        self.blocks.pop()

    def cur_block(self):
        return self.blocks[-1]

    def visitBlock(self, ctx: GuaParser.BlockContext):
        self.num += 1
        self.add_block()
        for k, v in self.temp_block.items():
            self.cur_block()[k] = v
        self.temp_block = {}

        r = ''

        statements_visit_result = []
        for s in ctx.statement():
            statements_visit_result.append(self.visit(s))

        for m in statements_visit_result:
            # if m is None:
            #     continue
            r += m

        return_statement = ctx.returnStatement()
        if return_statement is None:
            # TODO 从这里看，go 的 defer 有价值
            self.del_block()
            self.num -= 1
            return f'{r}'

        return_statement_visit_result = self.visit(return_statement)
        r += return_statement_visit_result

        self.del_block()
        self.num -= 1
        return f'{r}'

    def visitLabelStatementDefinition(self, ctx: GuaParser.LabelStatementDefinitionContext):
        k = ctx.IDENTIFIER().getText()
        v, type_string = self.visit(ctx.expression())
        self.cur_block()[k] = type_string
        if ctx.VALUETYPE() is not None:
            _type = output_type_string(ctx.VALUETYPE().getText())
            self.cur_block()[k] = _type
            return string_with_space(self.num, f'var {k} {_type} = {v}\n')
        elif ctx.LISTTYPE() is not None:
            label_type = ctx.LISTTYPE().getText()
            value_type = container_value_type_string(label_type)
            out_type = output_container_type_string(ctx.LISTTYPE().getText())

            self.cur_block()[k] = value_type
            return string_with_space(self.num, f'{out_type} {k}[]  = {v};\n')
        elif ctx.MAPTYPE() is not None:
            _type = output_type_string(ctx.MAPTYPE().getText())
            self.cur_block()[k] = _type
            return string_with_space(self.num, f'var {k} map{_type} = map{_type}{v}\n')
        else:
            type_string = output_type_string(type_string)
            return string_with_space(self.num, f'{type_string} {k} = {v};\n')

    def visitLabelStatementConst(self, ctx: GuaParser.LabelStatementConstContext):
        k = ctx.IDENTIFIER().getText()
        v, _ = self.visit(ctx.expression())

        return string_with_space(self.num, f'con {k} = {v}\n')

    def visitLabelStatementThisDefinition(self, ctx: GuaParser.LabelStatementThisDefinitionContext):
        k = ctx.IDENTIFIER().getText()
        v, type_string = self.visit(ctx.expression())
        if self.in_new_method:
            field_type = output_type_string(ctx.VALUETYPE().getText())
            field_map = self.class_field_map[self.current_class]
            field_map[k] = field_type
            return string_with_space(self.num, f'r.{k} = {v}\n')
        else:
            # TODO 这对应哪种情况
            return string_with_space(self.num, f'var this.{k} = {v}\n')

    def visitLabelStatementThisConst(self, ctx: GuaParser.LabelStatementThisConstContext):
        k = ctx.IDENTIFIER().getText()
        v, _ = self.visit(ctx.expression())

        return string_with_space(self.num, f'con this.{k} = {v}\n')

    def visitLabelStatementClassDefinition(self, ctx: GuaParser.LabelStatementClassDefinitionContext):
        k = ctx.IDENTIFIER().getText()
        v, _ = self.visit(ctx.expression())

        return string_with_space(self.num, f'var class.{k} = {v}\n')

    def visitLabelStatementClassConst(self, ctx: GuaParser.LabelStatementClassConstContext):
        k = ctx.IDENTIFIER().getText()
        v, _ = self.visit(ctx.expression())

        return string_with_space(self.num, f'con class.{k} = {v}\n')

    def visitLabelStatementWhile(self, ctx: GuaParser.LabelStatementWhileContext):
        check, _ = self.visit(ctx.expression())
        block = self.visit(ctx.block())

        result = string_with_space(self.num, f'while ({check}) {{\n')
        result += block
        result += string_with_space(self.num, f'}}\n')

        return result

    def visitLabelStatementBreak(self, ctx: GuaParser.LabelStatementBreakContext):
        return string_with_space(self.num, f'break;\n')

    def visitLabelStatementContinue(self, ctx: GuaParser.LabelStatementContinueContext):
        return string_with_space(self.num, f'continue;\n')

    def visitLabelStatementIf(self, ctx: GuaParser.LabelStatementIfContext):
        check, _ = self.visit(ctx.expression())
        block = self.visit(ctx.block())

        result = string_with_space(self.num, f'if ({check}) {{\n')
        result += block
        result += string_with_space(self.num, f'}}\n')

        return result

    def visitLabelStatementIfElse(self, ctx: GuaParser.LabelStatementIfElseContext):
        check, _ = self.visit(ctx.expression())
        if_block = self.visit(ctx.block(0))
        else_block = self.visit(ctx.block(1))

        result = string_with_space(self.num, f'if ({check}) {{\n')
        result += if_block
        result += string_with_space(self.num, f'}} else {{\n')
        result += else_block
        result += string_with_space(self.num, f'}}\n')

        return result

    def visitLabelStatementIfElseIf(self, ctx: GuaParser.LabelStatementIfElseIfContext):
        check, _ = self.visit(ctx.expression())
        block = self.visit(ctx.block())
        else_if_blocks = [self.visit(c) for c in ctx.elseIfClause()]

        result = string_with_space(self.num, f'if ({check}) {{\n')
        result += block
        for b in else_if_blocks:
            result += b
        result += string_with_space(self.num, f'}}\n')

        return result

    def visitLabelStatementIfElseIfElse(self, ctx: GuaParser.LabelStatementIfElseIfElseContext):
        check, _ = self.visit(ctx.expression())
        if_block = self.visit(ctx.block(0))
        else_if_blocks = [self.visit(c) for c in ctx.elseIfClause()]
        else_block = self.visit(ctx.block(1))

        result = string_with_space(self.num, f'if ({check}) {{\n')
        result += if_block
        for b in else_if_blocks:
            result += b
        result += string_with_space(self.num, f'}} else {{\n')
        result += else_block
        result += string_with_space(self.num, f'}}\n')

        return result

    def visitLabelStatementFor(self, ctx: GuaParser.LabelStatementForContext):
        init = self.visit(ctx.forInitClause())
        compare, _ = self.visit(ctx.expression())
        assign = self.visit(ctx.forAssignClause())
        block = self.visit(ctx.block())

        result = string_with_space(self.num, f'for ({init}; {compare}; {assign}) {{\n')
        result += block
        result += string_with_space(self.num, f'}}\n')

        return result

    def visitLabelStatementAssignVar(self, ctx: GuaParser.LabelStatementAssignVarContext):
        k = ctx.IDENTIFIER().getText()
        op = ctx.op.text
        v, _ = self.visit(ctx.expression())
        return string_with_space(self.num, f'{k} {op} {v};\n')

    def visitLabelStatementAssignThisField(self, ctx: GuaParser.LabelStatementAssignThisFieldContext):
        field = ctx.IDENTIFIER().getText()
        op = ctx.op.text
        value, _ = self.visit(ctx.expression())
        return string_with_space(self.num, f'this.{field} {op} {value}\n')

    def visitLabelStatementAssignClassField(self, ctx: GuaParser.LabelStatementAssignClassFieldContext):
        field = ctx.IDENTIFIER().getText()
        op = ctx.op.text
        value, _ = self.visit(ctx.expression())
        return string_with_space(self.num, f'class.{field} {op} {value}\n')

    def visitLabelStatementAssignField(self, ctx: GuaParser.LabelStatementAssignFieldContext):
        name = ctx.IDENTIFIER(0).getText()
        field = ctx.IDENTIFIER(1).getText()
        op = ctx.op.text
        value, _ = self.visit(ctx.expression())
        return string_with_space(self.num, f'{name}.{field} {op} {value}\n')

    def visitLabelStatementNewFunction(self, ctx: GuaParser.LabelStatementNewFunctionContext):
        self.in_new_method = True

        block = self.visit(ctx.block())
        parameter = self.visit(ctx.formalParameters())

        name = f'New{self.current_class}'
        return_type_string = f'*{self.current_class}'
        self.function_map[name] = return_type_string
        result = string_with_space(self.num, f'func {name}({parameter}) ({return_type_string}) {{\n')
        self.num += 1
        result += string_with_space(self.num, f'var r = &{self.current_class}{{}}\n')
        self.num -= 1
        result += block
        self.num += 1
        result += string_with_space(self.num, f'return r\n')
        self.num -= 1
        result += string_with_space(self.num, f'}}\n')

        self.in_new_method = False

        return result

    def visitLabelStatementFunction(self, ctx: GuaParser.LabelStatementFunctionContext):
        name = ctx.IDENTIFIER().getText()
        parameter = self.visit(ctx.formalParameters())
        return_parameter = ctx.returnParameters()
        block = self.visit(ctx.block())

        if self.current_class != '':
            if return_parameter is None:
                result = string_with_space(self.num, f'func (this *{self.current_class}) {name}({parameter}) {{\n')
            else:
                return_parameter = self.visit(return_parameter)
                result = string_with_space(self.num, f'func (this *{self.current_class}) {name}({parameter}) ({return_parameter}) {{\n')
                class_method_map = self.class_method_map[self.current_class]
                class_method_map[name] = return_parameter
        else:
            if return_parameter is None:
                result = string_with_space(self.num, f'void\n{name}({parameter}) {{\n')
            else:
                return_parameter = self.visit(return_parameter)
                result = string_with_space(self.num, f'{output_type_string(return_parameter)}\n{name}({parameter}) {{\n')
                self.function_map[name] = return_parameter
        result += block
        result += string_with_space(self.num, f'}}\n')

        return result

    def visitLabelStatementClass(self, ctx: GuaParser.LabelStatementClassContext):
        name = ctx.IDENTIFIER().getText()
        self.current_class = name

        self.class_field_map[self.current_class] = {}
        self.class_method_map[self.current_class] = {}

        self.num -= 1
        block = self.visit(ctx.block())
        self.num += 1

        field_map: t.Dict[str, str] = self.class_field_map[self.current_class]
        result = string_with_space(self.num, f'@interface {name}:NSObject {{\n')
        self.num += 1
        for k, v in field_map.items():
            result += string_with_space(self.num, f'{v} {k};\n')
        self.num -= 1
        result += string_with_space(self.num, f'}}\n@end\n')
        result += block

        self.current_class = ''

        return result

    def visitLabelStatementClassFunction(self, ctx: GuaParser.LabelStatementClassFunctionContext):
        name = ctx.IDENTIFIER().getText()
        parameter = self.visit(ctx.formalParameters())
        block = self.visit(ctx.block())

        result = string_with_space(self.num, f'con class.{name} = function({parameter}) {{\n')
        result += block
        result += string_with_space(self.num, f'}}\n')

        return result

    def visitLabelStatementFunctionCall(self, ctx: GuaParser.LabelStatementFunctionCallContext):
        r, _ = self.visit(ctx.functionCallItem())
        return string_with_space(self.num, f'{r};\n')

    def visitLabelStatementFunctionCallChain(self, ctx: GuaParser.LabelStatementFunctionCallChainContext):
        es = []
        for e in ctx.clainItem():
            r, _ = self.visit(e)
            es.append(r)
        return string_with_space(self.num, '.'.join(es) + '\n')

    def visitLabelStatementMethodCall(self, ctx: GuaParser.LabelStatementMethodCallContext):
        r, _ = self.visit(ctx.methodCallItem())
        return string_with_space(self.num, f'{r}\n')

    def visitLabelStatementMethodCallChain(self, ctx: GuaParser.LabelStatementMethodCallChainContext):
        m = self.visit(ctx.methodCallItem())
        es = []
        for e in ctx.clainItem():
            r, _ = self.visit(e)
            es.append(r)
        return string_with_space(self.num, m + '.' + '.'.join(es) + '\n')

    def visitReturnStatement(self, ctx: GuaParser.ReturnStatementContext):
        v, _ = self.visit(ctx.expression())
        return string_with_space(self.num, f'return {v};\n')

    def visitElseIfClause(self, ctx: GuaParser.ElseIfClauseContext):
        check, _ = self.visit(ctx.expression())
        block = self.visit(ctx.block())

        result = string_with_space(self.num, f'}} else if ({check}) {{\n')
        result += block

        return result

    def visitForInitClause(self, ctx: GuaParser.ForInitClauseContext):
        k = ctx.IDENTIFIER().getText()
        v, type_string = self.visit(ctx.expression())
        type_string = output_type_string(type_string)
        return f'{type_string} {k} = {v}'

    def visitForAssignClause(self, ctx: GuaParser.ForAssignClauseContext):
        a = ctx.IDENTIFIER().getText()
        op = ctx.op.text
        b, _ = self.visit(ctx.expression())
        return f'{a} {op} {b}'

    def visitLabelExpressionMulDivMod(self, ctx: GuaParser.LabelExpressionMulDivModContext):
        op = ctx.op.text
        a, a_type_string = self.visit(ctx.expression(0))
        b, b_type_string = self.visit(ctx.expression(1))
        return f'{a} {op} {b}', type_string_add(a_type_string, b_type_string)

    def visitLabelExpressionAddSub(self, ctx: GuaParser.LabelExpressionAddSubContext):
        op = ctx.op.text
        a, a_type_string = self.visit(ctx.expression(0))
        b, b_type_string = self.visit(ctx.expression(1))
        return f'{a} {op} {b}', type_string_add(a_type_string, b_type_string)

    def visitLabelExpressionBitMove(self, ctx: GuaParser.LabelExpressionBitMoveContext):
        op = ctx.op.text
        a, a_type_string = self.visit(ctx.expression(0))
        b, b_type_string = self.visit(ctx.expression(1))
        return f'{a} {op} {b}', type_string_add(a_type_string, b_type_string)

    def visitLabelExpressionBitAnd(self, ctx: GuaParser.LabelExpressionBitAndContext):
        a, a_type_string = self.visit(ctx.expression(0))
        b, b_type_string = self.visit(ctx.expression(1))
        return f'{a} & {b}', type_string_add(a_type_string, b_type_string)

    def visitLabelExpressionBitNot(self, ctx: GuaParser.LabelExpressionBitNotContext):
        a, a_type_string = self.visit(ctx.expression())
        return f'~{a}', a_type_string

    def visitLabelExpressionBitOr(self, ctx: GuaParser.LabelExpressionBitOrContext):
        a, a_type_string = self.visit(ctx.expression(0))
        b, b_type_string = self.visit(ctx.expression(1))
        return f'{a} | {b}', type_string_add(a_type_string, b_type_string)

    def visitLabelExpressionRelation(self, ctx: GuaParser.LabelExpressionRelationContext):
        op = ctx.op.text
        a, a_type_string = self.visit(ctx.expression(0))
        b, b_type_string = self.visit(ctx.expression(1))
        return f'{a} {op} {b}', 'bool'

    def visitLabelExpressionAnd(self, ctx: GuaParser.LabelExpressionAndContext):
        a, a_type_string = self.visit(ctx.expression(0))
        b, b_type_string = self.visit(ctx.expression(1))
        return f'{a} && {b}', type_string_add(a_type_string, b_type_string)

    def visitLabelExpressionNot(self, ctx: GuaParser.LabelExpressionNotContext):
        a, a_type_string = self.visit(ctx.expression())
        return f'!{a}', a_type_string

    def visitLabelExpressionOr(self, ctx: GuaParser.LabelExpressionOrContext):
        a, a_type_string = self.visit(ctx.expression(0))
        b, b_type_string = self.visit(ctx.expression(1))
        return f'{a} || {b}', type_string_add(a_type_string, b_type_string)

    def visitLabelExpressionThisFieldCall(self, ctx: GuaParser.LabelExpressionThisFieldCallContext):
        r = ctx.IDENTIFIER().getText()
        class_field_map = self.class_field_map[self.current_class]
        return f'this.{r}', class_field_map[r]

    def visitLabelExpressionThisCallChain(self, ctx: GuaParser.LabelExpressionThisCallChainContext):
        m = ctx.IDENTIFIER().getText()
        es = []
        type_string = ''
        for e in ctx.clainItem():
            r, type_string = self.visit(e)
            es.append(r)
        return 'this.' + m + '.' + '.'.join(es), type_string

    def visitLabelExpressionClassFieldCall(self, ctx: GuaParser.LabelExpressionClassFieldCallContext):
        r = ctx.IDENTIFIER().getText()
        # TODO 这里应该有类型返回
        return f'class.{r}', ''

    def visitLabelExpressionClassCallChain(self, ctx: GuaParser.LabelExpressionClassCallChainContext):
        m = ctx.IDENTIFIER().getText()
        es = []
        for e in ctx.clainItem():
            r, _ = self.visit(e)
            es.append(r)
        # TODO 这里应该有类型返回
        return 'class.' + m + '.' + '.'.join(es), ''

    def visitLabelExpressionFieldCall(self, ctx: GuaParser.LabelExpressionFieldCallContext):
        a = ctx.IDENTIFIER(0).getText()
        a_type_string = class_type_string(self.cur_block()[a])
        a_class_field_map = self.class_field_map[a_type_string]
        b = ctx.IDENTIFIER(1).getText()
        return f'{a}.{b}', a_class_field_map[b]

    def visitLabelExpressionNewCall(self, ctx: GuaParser.LabelExpressionNewCallContext):
        name = f'New{ctx.IDENTIFIER().getText()}'
        parameter = self.visit(ctx.actualParameters())
        return f'{name}({parameter})', self.function_map.get(name, '')

    def visitLabelExpressionMethodCall(self, ctx: GuaParser.LabelExpressionMethodCallContext):
        a = ctx.IDENTIFIER(0).getText()
        a_type_string = class_type_string(self.cur_block()[a])
        a_class_method_map = self.class_method_map[a_type_string]
        b = ctx.IDENTIFIER(1).getText()
        parameter = self.visit(ctx.actualParameters())
        return f'{a}.{b}({parameter})', a_class_method_map[b]

    def visitLabelExpressionCallChain(self, ctx: GuaParser.LabelExpressionCallChainContext):
        m = ctx.IDENTIFIER().getText()
        self.clain_item_type_string = self.cur_block()[m]
        es = []
        type_string = ''
        for e in ctx.clainItem():
            r, type_string = self.visit(e)
            es.append(r)
            self.clain_item_type_string = class_type_string(type_string)
        self.clain_item_type_string = ''
        return m + '.' + '.'.join(es), type_string

    def visitLabelExpressionFunctionCall(self, ctx: GuaParser.LabelExpressionFunctionCallContext):
        r, type_string = self.visit(ctx.functionCallItem())
        return f'{r}', type_string

    def visitLabelExpressionFunctionCallChain(self, ctx: GuaParser.LabelExpressionFunctionCallChainContext):
        m, type_string = self.visit(ctx.functionCallItem())
        self.clain_item_type_string = class_type_string(type_string)
        es = []
        type_string = ''
        for e in ctx.clainItem():
            r, type_string = self.visit(e)
            es.append(r)
            self.clain_item_type_string = class_type_string(type_string)
        self.clain_item_type_string = ''
        return m + '.' + '.'.join(es), type_string

    def visitLabelExpressionArray(self, ctx: GuaParser.LabelExpressionArrayContext):
        es = []
        for e in ctx.expression():
            r, _ = self.visit(e)
            es.append(r)
        # array 需要类型标注
        return '{' + ', '.join(es) + '}', ''

    def visitLabelExpressionMap(self, ctx: GuaParser.LabelExpressionMapContext):
        es = []
        for e in ctx.mapItem():
            r = self.visit(e)
            es.append(r)
        # map 需要类型标注
        return '{' + ', '.join(es) + '}', ''

    def visitLabelExpressionContainerCall(self, ctx: GuaParser.LabelExpressionContainerCallContext):
        a = ctx.IDENTIFIER().getText()
        b, _ = self.visit(ctx.expression())
        return f'{a}[{b}]', self.cur_block()[a]

    def visitLabelExpressionLiteralNull(self, ctx: GuaParser.LabelExpressionLiteralNullContext):
        r = ctx.NULL().getText()
        return f'{r}', ''

    def visitLabelExpressionLiteralFloat(self, ctx: GuaParser.LabelExpressionLiteralFloatContext):
        r = ctx.FLOAT().getText()
        return f'{r}', 'float'

    def visitLabelExpressionLiteralInt(self, ctx):
        r = ctx.INT().getText()
        return f'{r}', 'int'

    def visitLabelExpressionLiteralBool(self, ctx: GuaParser.LabelExpressionLiteralBoolContext):
        r = ctx.BOOL().getText()
        return f'{r}', 'bool'

    def visitLabelExpressionLiteralString(self, ctx: GuaParser.LabelExpressionLiteralStringContext):
        r = ctx.STRING().getText()
        return f'@{r}', 'string'

    def visitLabelExpressionIdentifier(self, ctx: GuaParser.LabelExpressionIdentifierContext):
        r = ctx.IDENTIFIER().getText()
        return f'{r}', self.cur_block().get(r, '')

    def visitMapItem(self, ctx: GuaParser.MapItemContext):
        a = ctx.STRING().getText()
        b, _ = self.visit(ctx.expression())
        # TODO 暂时觉得不需要类型返回
        return f'{a}: {b}'

    def visitFunctionCallItem(self, ctx: GuaParser.FunctionCallItemContext):
        a = ctx.IDENTIFIER().getText()
        parameter = self.visit(ctx.actualParameters())
        return f'{a}({parameter})', self.function_map.get(a, '')

    def visitMethodCallItem(self, ctx: GuaParser.MethodCallItemContext):
        a = ctx.IDENTIFIER(0).getText()
        a_type_string = class_type_string(self.cur_block()[a])
        a_class_method_map = self.class_method_map[a_type_string]
        b = ctx.IDENTIFIER(1).getText()
        parameter = self.visit(ctx.actualParameters())
        return f'{a}.{b}({parameter})', a_class_method_map[b]

    def visitClainItem(self, ctx: GuaParser.ClainItemContext):
        if ctx.IDENTIFIER() is not None:
            r = ctx.IDENTIFIER().getText()
            class_field_map = self.class_field_map[self.clain_item_type_string]
            type_string = class_field_map[r]
            return f'{r}', type_string
        else:
            r, _ = self.visit(ctx.functionCallItem())
            if self.clain_item_type_string in self.class_method_map.keys():
                class_method_map = self.class_method_map[self.clain_item_type_string]
                type_string = class_method_map[method_name(r)]
            else:
                type_string = 'string'
            return f'{r}', type_string

    def visitFormalParameters(self, ctx: GuaParser.FormalParametersContext):
        es = []
        length = len(ctx.IDENTIFIER())
        for i in range(length):
            k = ctx.IDENTIFIER(i).getText()
            v = ctx.VALUETYPE(i).getText()
            self.temp_block[k] = v
            es.append(output_type_string(v) + ' ' + k)
        return ', '.join(es)

    def visitReturnParameters(self, ctx: GuaParser.ReturnParametersContext):
        return ctx.VALUETYPE().getText()

    def visitActualParameters(self, ctx: GuaParser.ActualParametersContext):
        es = []
        for e in ctx.expression():
            r, _ = self.visit(e)
            es.append(r)
        return ', '.join(es)


def main():
    import antlr4 as ant
    # 写死了读取 main.gua
    path = 'main.gua'
    fs = ant.FileStream(path, encoding='utf-8')
    lexer = GuaLexer(fs)
    tokens = ant.CommonTokenStream(lexer)
    ast = GuaParser(tokens).block()
    visitor = EvalVisitor()
    output = visitor.visit(ast)
    with open("../test-oc/create.m", "w") as f:
        f.write("#import <Foundation/Foundation.h>\n\n")
        f.write("#define log NSLog\n\n\n")
        f.write(output)


if __name__ == '__main__':
    main()
