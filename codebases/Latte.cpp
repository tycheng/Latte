#include "Latte.h"

void read_libsvm(vector<vector<float>> &features, vector<int> &labels, string &filename, int n_features, int &n_labels) {
    ifstream in(filename, std::ifstream::in);
    // check the validity of the input file
    if (!in.good()) {
        cerr << "Cannot read file: " << filename << endl;
        exit(EXIT_FAILURE);
    }

    // reading from the libsvm data set
    for (string line; getline(in, line); ) {
        // create a new vector to store this data instance
        features.push_back(vector<float>());
        vector<float> &tokens = features.back();

        // split the string and load the data
        size_t start = 0, end = 0;
        for (n_features = 0; (end = line.find(":", start)) != string::npos; n_features++) {
            string str = line.substr(start, end - start);
            start = end + 1;
            if (n_features == 0) labels.push_back(stoi(str));      // the first integer is label
            else                 tokens.push_back(stof(str));      // the following are features
        }
    }
    in.close();
    n_features--;   // the first is label, do not count it
    n_labels = labels.size();
    return ;
}

Ensemble* LibsvmDataLayer(Network &net, string train_file, string test_file, int n_features, int &n_labels) {
    vector<vector<float>> &train_features = net.get_train_features();
    vector<vector<float>> &test_features = net.get_test_features();
    vector<int> &train_labels = net.get_train_labels();
    vector<int> &test_labels = net.get_test_labels();

    read_libsvm(train_features, train_labels, train_file, n_features, n_labels);
    read_libsvm(test_features, test_labels, test_file, n_features, n_labels);
    // TODO: this function is not finished yet
    // How do we arrange the data, SoA directly, or AoS -> SoA?
    return nullptr;
}

Ensemble* FullyConnectedLayer(Network &net, Ensemble &prev_ensemble, int N) {
    return nullptr;
}

Ensemble* SoftmaxLossLayer(Network &net, Ensemble &prev_ensemble, int n_labels) {

    return nullptr;
}

void add_connection(Network& net, Ensemble& enm1, Ensemble& enm2, Connection &connection) {

    return;
}

void shared_variable_analsyis() {

    return;
}

void Xaiver_initialize() {

    return;
}

/*
Ensemble& Network::create_ensemble(Dim dim) {
    ensembles.push_back(Ensemble(dim));
    return ensembles.back();
}
*/


int ITERATIONS = 1000;
void solve (Network& network, Solver& solver) {
    
    // 1. mapping to shared memory region
    // INPUT: network architecture
    // OUTPUT: compact memory allocation of computing neurons 
    shared_variable_analsyis(); 
    // 2. initialize the connection (weights) parameter of network 
    Xaiver_initialize();
    // 3. 
    for (int iter = 0; iter < ITERATIONS; iter++) {
        // 4. forward routine through pattern matching

        // 5. backward routine through pattern matching 
        // (solver like sgd is used here..)

        // 6. update weight
    }
    // 7. evaluate accuracy and timing performance
    // evaluate ();
    
}

int main (int argn, char** argv) {
    double* haha = init_mkl_mat(5, 5);
    Xaiver_initialize(haha, 25, 30);
    for (int i = 0; i < 5; i ++) {
        for (int j = 0; j < 5; j ++) {
            cout << *(haha+5*i+j) << " ";
        }
        cout << endl;
    }
    mkl_free(haha);
#if 0
    Network net1;
    Network net2;
    Network net3;
    cout << "[net1] " << net1.get_string() << endl;
    cout << "[net2] " << net2.get_string() << endl;
    cout << "[net3] " << net3.get_string() << endl;

    Neuron neuron1;
    Neuron neuron2;
    Neuron neuron3;
    cout << "[neuron1] " << neuron1.get_string() << endl;
    cout << "[neuron2] " << neuron2.get_string() << endl;
    cout << "[neuron3] " << neuron3.get_string() << endl;

    /* TODO: more unit tests here */
#endif
}
