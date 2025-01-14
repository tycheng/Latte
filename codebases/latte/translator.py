import ast
from ast_matcher import *
from templates import *
from copy import deepcopy
from term import *
from structures import *

function_args = {
    "sgemm_dp": [ 3, 1, 1, 1 ],
    "sgemm_axpy": [ 3, 1, 1, 1 ],
    "sgemm_copy": [ 3, 1, 1 ],
    "sgemm_zeros": [ 3, 1 ]
}

def unwrap(node):
    if isinstance(node, DereferenceNode):
        return unwrap(node.children[0])
    if isinstance(node, IndexNode):
        return unwrap(node.base_addr)
    # if isinstance(node, ArrayNode):
    #     if node.indices[0] == "tid":
    #         return node
    #     return unwrap(node.base_addr)
    return node

def match_forloop(stmt):
    tmpls = [ template_for("range"), template_for("xrange") ]
    for tmpl in tmpls:
        if tmpl.match(stmt):
            return tmpl.wildcard
    return None

class Translator(object):
    """
    Translator translates from Python AST to
    self-defined structure, since Python AST
    is complicated to manipulate
    """
    def __init__(self, neuron_analyzer, prev_neuron_analyzer, curr_enm, prev_enm, conn_type, share_weights, MKL_FLAG, DP_FLAG ):
        super(Translator, self).__init__()
        self.neuron_analyzer = neuron_analyzer
        self.prev_neuron_analyzer = prev_neuron_analyzer
        self.curr_enm = curr_enm
        self.prev_enm = prev_enm
        self.statements = []
        # getting the dimension from analyzer for constant replacement
        self.curr_enm_dim = neuron_analyzer.curr_enm_dim()
        self.prev_enm_dim = neuron_analyzer.prev_enm_dim()
        # connections
        self.connection = conn_type
        self.share_weights = share_weights
        # set pattern match flag
        self.MKL_FLAG = MKL_FLAG
        self.DP_FLAG = DP_FLAG

    def process_stmt(self, stmt):
        # ignore the stmts for syntax and debug
        if isinstance(stmt, ast.Pass): return
        if isinstance(stmt, ast.Assert): return
        # process stmt of each type
        if isinstance(stmt, ast.Assign):
            return self.process_assign(stmt)
        if isinstance(stmt, ast.For):
            return self.process_for(stmt)
        # We cannot process this statement, so we print it for debug
        term.dump("PROCESS STMT(NO MATCH): %s" % ast.dump(stmt), term.WARNING)

    def process_assign(self, node):
        _, dim_y = self.curr_enm_dim
        # pattern match
        if self.MKL_FLAG:
            # hard code the tid if DP_FLAG is enabled
            subscript = "[tid]" if self.DP_FLAG else ""

            # try pattern match a bunch of different patterns
            tmpl = template_asgn("output")
            if tmpl.prefix_of(node):
                expr = self.process_node(tmpl.wildcard['exp'])
                return AssignmentNode(IndexNode(\
                        ConstantNode(self.curr_enm+"_output%s" % subscript), ['x', 'y'], dim_y), \
                        expr)

            tmpl = template_asgn("grad_activation")
            if tmpl.prefix_of(node):
                expr = self.process_node(tmpl.wildcard['exp'])
                return AssignmentNode(IndexNode(\
                        ConstantNode(self.curr_enm+"_grad_activation%s" % subscript), ['x', 'y'], dim_y), \
                        expr)

            tmpl = template_asgn("grad_output")
            if tmpl.prefix_of(node):
                expr = self.process_node(tmpl.wildcard['exp'])
                return AssignmentNode(IndexNode(\
                        ConstantNode(self.curr_enm+"_grad_output%s" % subscript), ['x', 'y'], dim_y), \
                        expr)

        # assign node
        var_name = self.process_node(node.targets[0])
        var_value = self.process_node(node.value)
        return AssignmentNode(var_name, var_value)

    def process_for(self, node):
        # pattern match
        if self.MKL_FLAG:
            # hard code the tid if DP_FLAG is enabled
            subscript = "[tid]" if self.DP_FLAG else ""

            #tmpl = template_dp("self", "output")
            tmpl = template_fp_dp()
            matched = tmpl.match(node) 
            if matched:
                print ast.dump(tmpl.wildcard['B'])
                A, C, B, i,  _, j = map(self.process_node, tmpl.wildcard.values())
                call = CallNode(ConstantNode("sgemm_dp"))
                call.add_arg(C, 1, 1)
                call.add_arg(A, 1, 0)
                call.add_arg(B, 1, 0)
                call.add_arg(ConstantNode(self.prev_enm_dim[0] * self.prev_enm_dim[1]), 1, 0)
                return call

            tmpl = template_bp_axpy()
            matched = tmpl.match(node)
            # print ast.dump(node)
            ''' self.grad_weights[prev.pos_x][prev.pos_y] += 
                            self.grad_output * self.inputs[prev.pos_x][prev.pos_y] '''
            if matched:
                #for x in map(self.process_node, tmpl.wildcard.values()): print x
                C, B, _, _, scalar, _ = map(self.process_node, tmpl.wildcard.values())
                call = CallNode(ConstantNode("sgemm_axpy"))
                call.add_arg(C, 1, 1)
                call.add_arg(DereferenceNode(scalar), 1, 0)
                call.add_arg(B, 1, 0)
                call.add_arg(ConstantNode(self.prev_enm_dim[0] * self.prev_enm_dim[1]), 1, 0)
                return call

            tmpl = template_bp_scalar_prod()
            matched = tmpl.match(node) 
            ''' prev.grad_output += self.grad_output * self.weights[prev.pos_x][prev.pos_y] '''
            if matched:
                #for x in map(self.process_node, tmpl.wildcard.values()): print x
                C, B,  _, _, scalar, _ = map(self.process_node, tmpl.wildcard.values())
                prev_type = self.neuron_analyzer.prev_enm_type()
                if prev_type is None or prev_type.endswith("DataLayer"):
                    return None
                C = ConstantNode(self.prev_enm + "_grad_output%s" % subscript)
                call = CallNode(ConstantNode("sgemm_axpy"))
                call.add_arg(unwrap(C), 1, 1)
                call.add_arg(DereferenceNode(scalar), 1, 0)
                call.add_arg(B, 1, 0)
                call.add_arg(ConstantNode(self.prev_enm_dim[0] * self.prev_enm_dim[1]), 1, 0)
                return call

        # ---------------------------------------------------------------------

        # match for-backward-adj loop
        tmpl = template_for_backward_adj()
        if tmpl.match(node):
            result = tmpl.wildcard
            elt, indices = self.process_adjacency([])
            index = indices[elt[0].get_constant()]
            #print index
            for_i = ForNode(ConstantNode("i"), ConstantNode(index[0]),\
                            ConstantNode(index[1]), ConstantNode(index[2]))
            index = indices[elt[1].get_constant()]
            for_j = ForNode(ConstantNode("j"), ConstantNode(index[0]),\
                            ConstantNode(index[1]), ConstantNode(index[2]))
            for_i.add_child(for_j)
            #print "=====>" , for_i
            for stmt in result['body']:
                for_j.add_child(self.process_stmt(stmt))
            return for_i

        # ---------------------------------------------------------------------

        # match for-range loop
        result = match_forloop(node)
        if result is None:
            term.dump("PROCESS FOR STMT(ERROR): %s" % ast.dump(node), term.FAIL)
            return
        # extract information from forloop
        initial_name = self.process_node(result['i'])
        initial = ConstantNode(0)
        loop_bound = self.process_node(result['N'])
        increment = ConstantNode(1)
        # print loop_bound
        # print result['N']
        for_node = ForNode(initial_name, initial, loop_bound, increment)
        # append the inner codes to the loop
        codes = result['body']
        if not isinstance(codes, list):
            codes = [ codes ]
        for stmt in codes:
            for_node.add_child(self.process_stmt(stmt))
        return for_node

    def process_node(self, node):
        # parse the variable name, and create structure
        if isinstance(node, str) or isinstance(node, int) or \
           isinstance(node, float):
            return ConstantNode(node)
        if isinstance(node, ast.Num):
            return ConstantNode(node.n)
        if isinstance(node, ast.Name):
            return ConstantNode(node.id)
        if isinstance(node, ast.BinOp):
            l = self.process_node(node.left)
            r = self.process_node(node.right)
            op = self.process_op(node.op)
            return ExpressionNode(l, r, op)
        if isinstance(node, ast.Subscript):
            return self.process_subscript(node)
        if isinstance(node, ast.Index):
            return self.process_node(node.value)
        if isinstance(node, ast.Attribute):
            return self.process_attribute(node)
        if isinstance(node, ast.Call):
            return self.process_call(node)
        term.dump("PROCESS NODE(NO MATCH): %s" % ast.dump(node), term.WARNING)

    def process_call(self, node):
        func_name = self.process_node(node.func)
        func_args = map(self.process_node, node.args)
        node = CallNode(func_name)
        # default all arguments are read only
        arg_flags = [ 1 ] * len(func_args)
        # check if the function falls in our special functions: sgemm
        if func_name in function_args:
            arg_flags = function_args[func_name]
            assert len(arg_flags) == len(func_args)
        # fill the CallNode with arguments
        for arg, flag in zip(func_args, arg_flags):
            node.add_arg(arg, flag&0x1, flag&0x2)
        return node

    def process_subscript(self, node):
        array_name = self._find_array_name(node)
        array_idx = self._find_array_index(node)
        # return IndexNode(array_name, array_idx, self.prev_enm_dim[1])
        return IndexNode(array_name, array_idx, self.curr_enm_dim[1])

    def _find_array_name(self, node):
        if isinstance(node, ast.Name):
            return ConstantNode(node.id)
        if isinstance(node, ast.Attribute):
            return self.process_attribute(node)
        assert isinstance(node, ast.Subscript)
        return self._find_array_name(node.value)

    def _find_array_index(self, node):
        if isinstance(node, ast.Name):
            return self.process_node(node)
        if isinstance(node, ast.Index):
            return self._find_array_name(node.value)
        assert isinstance(node, ast.Subscript)
        if isinstance(node.value, ast.Subscript):
            return self._find_array_index(node.value) + [ self.process_node(node.slice) ]
        return [ self._find_array_index(node.slice) ]

    def process_op(self, op):
        if isinstance(op, ast.Add):
            return "+"
        elif isinstance(op, ast.Sub):
            return "-"
        elif isinstance(op, ast.Mult):
            return "*"
        elif isinstance(op, ast.Div):
            return " / "
        elif isinstance(op, ast.Pow):
            return "pow"
        term.dump("PROCESS OP(INVALID OP): %s" % op, term.FAIL)

    def process_attribute(self, node):
        owner = self.process_node(node.value)
        attr = node.attr
        if str(owner) == "self" or str(owner) == "prev":
            # built-in dimension analysis
            if str(owner) == "self":
                enm_name = self.curr_enm
                if attr == "prev_dim_x":
                    return ConstantNode(self.prev_enm_dim[0])
                if attr == "prev_dim_y":
                    return ConstantNode(self.prev_enm_dim[1])
                if attr == "dim_x":
                    return ConstantNode(self.curr_enm_dim[0])
                if attr == "dim_y":
                    return ConstantNode(self.curr_enm_dim[1])
                if attr.endswith("label"):
                    return ArrayNode(ConstantNode("cur_label"), ['x', 'y'])
                #############################################
                # replace inputs with outputs from last layer
                # this is done to fit the current design
                # we might want to follow the paper and do
                # input copy from last layer if the inputs
                # are not shared
                if attr.endswith("inputs"):
                    if not self.DP_FLAG:
                        var_name = "%s_output" % self.prev_enm
                        return ConstantNode(var_name)
                    else:
                        var_name = "%s_output" % self.prev_enm
                        return ArrayNode(ConstantNode(var_name), ['tid'])
                #############################################
                # analyze field type
                field_type = self.neuron_analyzer.get_field_type(attr)
                dim_y = self.curr_enm_dim[1]
            else:   # must be prev
                enm_name = self.prev_enm
                if attr == "pos_x":
                    return ConstantNode("i")
                elif attr == "pos_y":
                    return ConstantNode("j")
                # analyze field type
                if self.prev_neuron_analyzer is not None:
                    field_type = self.prev_neuron_analyzer.get_field_type(attr)
                else:
                    field_type = None
                dim_y = self.prev_enm_dim[1]

            # special case during data parallelism
            if self.DP_FLAG:
                if attr.endswith("grad_weights"):
                    var_name = "%s_%s" % (enm_name, attr)
                    return ArrayNode(ArrayNode(\
                            ConstantNode(var_name), ['tid']), ['x', 'y'])

            # special case during shared weights:
            if self.neuron_analyzer.share_weights and attr.endswith("weights"):
                var_name = "%s_%s" % (enm_name, attr)
                # for ensembles that share weights, we just need to return
                # the weight itself, not weight[x][y]
                return ConstantNode(var_name)

            # general process based on the type of field
            if field_type is None:
                return ConstantNode(enm_name + "_" + attr)
            elif field_type == "vector<vector<float*>>":
                # 2D fields
                var_name = "%s_%s" % (enm_name, attr)
                # term.dump("///////> %s" % var_name, term.WARNING)
                return ArrayNode(\
                        ConstantNode(var_name), ['x', 'y'])
            else:
                var_name = "%s_%s" % (enm_name, attr)
                # term.dump("=======> %s" % var_name, term.OKBLUE)
                # 1D fields
                # transform to SoA form
                if not self.DP_FLAG:
                    # term.dump("-------> %s" % var_name, term.OKGREEN)
                    # disable data parallelism
                    return IndexNode(\
                            ConstantNode(var_name), ['x', 'y'], dim_y)
                else:
                    # term.dump("+++++++> %s" % var_name, term.FAIL)
                    # enable data parallelism
                    return IndexNode(\
                            ArrayNode(var_name, ['tid']), ['x', 'y'], dim_y)
        else:
            # calls like np.tanh, suffice to only return the attr
            return ConstantNode(node.attr)

    def process_adjacency(self, stmts):
        if self.connection is None: return
        assert isinstance(self.connection, ast.Lambda)
        assert isinstance(self.connection.body, ast.ListComp)
        args = self.connection.args
        args = map(self.process_node, args.args)
        body = self.connection.body
        elt = map(self.process_node, body.elt.elts)
        gen = body.generators
        # print ast.dump(body)
        assert len(gen) == 2
        assert isinstance(gen[0].target, ast.Name)
        assert isinstance(gen[1].target, ast.Name)
        assert isinstance(gen[0].iter, ast.Call)
        assert isinstance(gen[1].iter, ast.Call)
        assert gen[0].iter.func.id == "range"
        assert gen[1].iter.func.id == "range"
        indices = {
            gen[0].target.id: map(self.process_node, gen[0].iter.args),
            gen[1].target.id: map(self.process_node, gen[1].iter.args)
        }
        # transform the loop bound into range format
        for key in indices.iterkeys():
            if len(indices[key]) == 1:
                indices[key] = [0] + indices[key] + [1]
            elif len(indices[key]) == 2:
                indices[key] = indices[key] + [1]
        return elt, indices
