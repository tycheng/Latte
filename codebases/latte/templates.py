from ast_matcher import template

"""
Templates for input scripts
"""

@template
def template_Network():
    _name = Network() 

@template
def template_FullyConnectedLayer():
    _name = FullyConnectedLayer(_net, _prev, _dim_x, _dim_y, _Neuron)

@template
def template_LibsvmDataLayer():
    _name = LibsvmDataLayer(_net, _train, _test, _dim_x, _dim_y, _Neuron)

@template
def template_SoftmaxLossLayer():
    _name = SoftmaxLossLayer(_net, _prev, _dim_x, _dim_y, _Neuron)

@template
def template_Ensemble():
    _net.add_ensemble(_cur_enm)

@template
def template_SGD():
    _name = SGD(_iter, _step)

@template
def template_add_connection():
    add_connection(_net, _prev_enm, _cur_enm, _mappings)

''' list of templates for layers '''
layer_templates = [
        template_LibsvmDataLayer(),
        template_FullyConnectedLayer(),
        template_SoftmaxLossLayer()
]

"""
Templates for computation programming paradigm
"""

@template
def template_for(range):
    for _i in range(_N):
        _body

@template
def template_for_range(range):
    for _i in range(len(_array)):
        _body

for_templates = [ template_for_range("range"), template_for_range("xrange") ]


@template
def template_dot_product(range):
    for _i in range(_dim_x):
        for _j in range(_dim_y):
            _dp_result = _dp_result + _A[_i][_j] * _B[_i][_j] 

@template
def template_fp_output():
    self.output = _exp

@template
def template_fp_activation():
    self.grad_activation = _exp

@template
def template_bp_activation():
    self.grad_output = _exp

@template
def template_bp_scalar_prod():
    for _i in range(_dim_x):
        for _j in range(_dim_y):
            self.grad_inputs[_i][_j] = _alpha * _B[_i][_j]

@template
def template_bp_axpy():
    for _i in range(_dim_x):
        for _j in range(_dim_y):
            _C[_i][_j] = _C[_i][_j] + _scalar * _B[_i][_j]

