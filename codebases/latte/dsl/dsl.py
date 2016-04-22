import compiler, inspect
import compiler.ast
from abc import abstractmethod

# global list of networks
network_list = []

ensemble_id_counter = 0
neuron_id_counter = 0
network_id_counter = 0

# The following functions simply allocate ids for neurons,
# ensembles, and networks
def allocate_neuron_id():
    global neuron_id_counter
    assigned_id = neuron_id_counter
    neuron_id_counter += 1
    return assigned_id

def allocate_ensemble_id():
    global ensemble_id_counter
    assigned_id = ensemble_id_counter
    ensemble_id_counter += 1
    return assigned_id

def allocate_network_id():
    global network_id_counter
    assigned_id = network_id_counter
    network_id_counter += 1
    return assigned_id

#  _   _      _                      _
# | \ | | ___| |___      _____  _ __| | __
# |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ /
# | |\  |  __/ |_ \ V  V / (_) | |  |   <
# |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\
#
class Network(object):
    """
        Network: Container for the whole graph network.
                 All operations: create_ensemble, create_layer, etc
                 should be initiated by the network
    """
    def __init__(self):
        super(Network, self).__init__()
        self.ID = allocate_network_id()
        self.ensembles = {}
        self.layers = {}
        # adding the new network into global network list
        network_list.append(self)

    def create_ensemble(self, neuron_type, dim):
        """ create a new ensemble in this network """
        ensemble = Ensemble(neuron_type, dim)
        self.ensembles[ensemble.ID] = ensemble
        return ensemble

    def add_connections(self, ensemble_source, ensemble_sink, connections):
        """ create a new layer and add connections in this layer """
        index = (ensemble_source.ID, ensemble_sink.ID)
        if index in self.layers:
            layer = self.layers[index]
        else:
            layer = Layer(ensemble_source, ensemble_sink, connections)
            self.layers[index] = layer
        return

    def solve(self):
        print "Code Generation Unimplemented"
        self._shared_variable_analysis_()

    def _shared_variable_analysis_(self):
        pass


#  _   _
# | \ | | ___ _   _ _ __ ___  _ __
# |  \| |/ _ \ | | | '__/ _ \| '_ \
# | |\  |  __/ |_| | | | (_) | | | |
# |_| \_|\___|\__,_|_|  \___/|_| |_|
#
class Neuron(object):
    """
        Neuron: Base type for neuron.
                Each neuron subtype should inherit
                Neuron type for common fields
    """
    def __init__(self):
        super(Neuron, self).__init__()
        self.ID = allocate_neuron_id()

        # basic requirements
        self.value = 0.0               # type Float32
        self.gradient = 0.0            # type Float32
        self.inputs = [[]]             # type Vector<Vector>
        self.gradient_inputs = [[]]    # type Vector<Vector>

    @abstractmethod
    def forward(self):
        """
        describe forward propagation to next ensemble;
        must be user-defined
        """
        return

    @abstractmethod
    def backward(self):
        """
        describe backward propagation to next ensemble;
        must be user-defined
        """
        return

#  _____                          _     _
# | ____|_ __  ___  ___ _ __ ___ | |__ | | ___
# |  _| | '_ \/ __|/ _ \ '_ ` _ \| '_ \| |/ _ \
# | |___| | | \__ \  __/ | | | | | |_) | |  __/
# |_____|_| |_|___/\___|_| |_| |_|_.__/|_|\___|
#
class Ensemble(object):
    """
        Ensemble: A group of neurons of same level
    """
    def __init__(self, neuron_type, dim):
        super(Ensemble, self).__init__()
        self.ID = allocate_ensemble_id()
        self.neuron_type = neuron_type

        # create neurons in this ensemble
        if isinstance(dim, int):
            # single dimension neuron network will be 
            # implicitly converted to 2D neuron network
            dim = 1, dim

        # otherwise dim is a row x column object
        r, c = dim

        self.neurons = [ [neuron_type() for i in xrange(c)] for j in xrange(r) ]
        self.connections = dict()

    def get_neuron_at(self, index):
        if isinstance(index, int):
            # single dimension neuron network will be 
            # implicitly converted to 2D neuron network
            index = 0, index
        r, c = index
        return self.neurons[r][c]

    def add_connection(self, idx1, idx2):
        # convert the single dimension index to two dimensions
        if isinstance(idx1, int):
            idx1 = 0, idx1
        if isinstance(idx2, int):
            idx2 = 0, idx2
        # check if this index already has connections
        if idx1 not in self.connections:
            self.connections[idx] = set()
        # add connection
        self.connections[idx].add(idx2)

#  _
# | |    __ _ _   _  ___ _ __
# | |   / _` | | | |/ _ \ '__|
# | |__| (_| | |_| |  __/ |
# |_____\__,_|\__, |\___|_|
#             |___/
#
class Layer(object):

    """
        Layer: connection manager between two ensembles
    """

    def __init__(self, source, sink, connections):
        super(Layer, self).__init__()
        self.ensemble_source = source
        self.ensemble_sink = sink
        self.connections = connections

    def get_forward_ast(self):
        """ return forward function AST from source neurons """
        source = inspect.getsource(self.ensemble_source.neuron_type)
        module = compiler.parse(source)
        function = self._get_function_(module, "forward")
        assert function is not None
        return function.code

    def get_backward_ast(self):
        """ return backward function AST from sink neurons """
        source = inspect.getsource(self.ensemble_sink.neuron_type)
        module = compiler.parse(source)
        function = self._get_function_(module, "backward")
        assert function is not None
        return function.code

    def _get_function_(self, ast, func_name):
        """ helper function to find function in AST by name"""
        for node in ast.getChildren():
            if node is None: continue
            if isinstance(node, compiler.ast.Function):
                if node.name == func_name:
                    return node
            elif isinstance(node, compiler.ast.Node):
                ret = self._get_function_(node, func_name)
                if ret: return ret
            elif isinstance(node, list):
                ret = self._get_function_(node, func_name)
                if ret: return ret
        return None
