#include "seal/seal.h"
#include <iostream>
#include <vector>
#include <memory>

using namespace std;
using namespace seal;

class SigmoidHomomorphic {
private:
    size_t poly_modulus_degree = 8192;
    uint64_t plain_modulus_value;

    shared_ptr<SEALContext> context;
  
    unique_ptr<Encryptor> encryptor;
    unique_ptr<Decryptor> decryptor;
  
    unique_ptr<Evaluator> evaluator;
    unique_ptr<BatchEncoder> encoder;
  
    RelinKeys relin_keys;
    Plaintext coeff_half, coeff_quarter, coeff_neg_1_48, coeff_1_480, coeff_neg_17_80640;

    SEALContext create_context() {
        EncryptionParameters parms(scheme_type::bfv);
      
        parms.set_poly_modulus_degree(poly_modulus_degree);
        parms.set_coeff_modulus(CoeffModulus::BFVDefault(poly_modulus_degree));
        parms.set_plain_modulus(PlainModulus::Batching(poly_modulus_degree, 20));
      
        return SEALContext(parms);
    }

    void init() {
        context = make_shared<SEALContext>(create_context());
        KeyGenerator keygen(*context);

        PublicKey public_key;
        keygen.create_public_key(public_key);
        encryptor = make_unique<Encryptor>(*context, public_key);

        SecretKey secret_key = keygen.secret_key();
        decryptor = make_unique<Decryptor>(*context, secret_key);
        evaluator = make_unique<Evaluator>(*context);
        encoder = make_unique<BatchEncoder>(*context);

        keygen.create_relin_keys(relin_keys);
        plain_modulus_value = context->first_context_data()->parms().plain_modulus().value();
        init_sigmoid_coefs();
    }

    void init_sigmoid_coefs() {
        // Taylor series for sigmoid = 1/2 + x/4 - x^3/48 + x^5/480 - 17*x^7/80640
      
        uint64_t inv_2 = compute_inverse(2);
        uint64_t inv_4 = compute_inverse(4);
        uint64_t inv_48 = compute_inverse(48);
        uint64_t inv_480 = compute_inverse(480);
        uint64_t inv_80640 = (compute_inverse(80640) * 17) % plain_modulus_value;

        coeff_half = encode_plain(inv_2);
        coeff_quarter = encode_plain(inv_4);
        coeff_neg_1_48 = encode_plain(inv_48);
        coeff_1_480 = encode_plain(inv_480);
        coeff_neg_17_80640 = encode_plain(inv_80640);
    }

    Ciphertext encrypt(uint64_t x) {
        vector<uint64_t> x_vec(poly_modulus_degree, x);
        Plaintext x_plain;
        encoder->encode(x_vec, x_plain);

        Ciphertext x_encrypted;
        encryptor->encrypt(x_plain, x_encrypted);
        return x_encrypted;
    }

    Ciphertext compute_sigmoid(const Ciphertext &x_encrypted) {
        Ciphertext result = x_encrypted;
        evaluator->multiply_plain_inplace(result, coeff_quarter);
        evaluator->relinearize_inplace(result, relin_keys);

        Ciphertext x2;
        evaluator->square(x_encrypted, x2);
        evaluator->relinearize_inplace(x2, relin_keys);
      
        Ciphertext x3;
        evaluator->multiply(x2, x_encrypted, x3);
        evaluator->relinearize_inplace(x3, relin_keys);
        evaluator->multiply_plain_inplace(x3, coeff_neg_1_48);

        Ciphertext x5;
        evaluator->multiply(x3, x2, x5);
        evaluator->relinearize_inplace(x5, relin_keys);
        evaluator->multiply_plain_inplace(x5, coeff_1_480);

        Ciphertext x7;
        evaluator->multiply(x5, x2, x7);
        evaluator->relinearize_inplace(x7, relin_keys);
        evaluator->multiply_plain_inplace(x7, coeff_neg_17_80640);

        evaluator->add_plain_inplace(result, coeff_half);
        evaluator->add_inplace(result, x3);
        evaluator->add_inplace(result, x5);
        evaluator->add_inplace(result, x7);

        return result;
    }

    uint64_t decrypt(const Ciphertext &encrypted_result) {
        Plaintext result_plain;
        decryptor->decrypt(encrypted_result, result_plain);

        vector<uint64_t> result_vec;
        encoder->decode(result_plain, result_vec);
        return result_vec.empty() ? 0 : result_vec[0];
    }

    double to_decimal(uint64_t integer_result) {
        return static_cast<double>(integer_result) / plain_modulus_value;
    }

    uint64_t compute_inverse(uint64_t divisor) {
        uint64_t inv = 1, base = divisor, mod = plain_modulus_value, exponent = mod - 2;
        while (exponent) {
            if (exponent % 2) inv = (inv * base) % mod;
            base = (base * base) % mod;
            exponent /= 2;
        }
        return inv;
    }

    Plaintext encode_plain(uint64_t value) {
        vector<uint64_t> vec(poly_modulus_degree, value);
        Plaintext encoded;
        encoder->encode(vec, encoded);
        return encoded;
    }

public:
    SigmoidHomomorphic() {
        init();
    }

    void run(uint64_t x) {
        Ciphertext encrypted_x = encrypt(x);
        Ciphertext sigmoid_result = compute_sigmoid(encrypted_x);
        uint64_t decrypted_result = decrypt(sigmoid_result);
        double decimal_result = to_decimal(decrypted_result);

        cout << "Decrypted result (integer): " << decrypted_result << endl;
        cout << "Decrypted result (decimal): " << decimal_result << endl;
    }
};

int main() {
    SigmoidHomomorphic sigmoid;
    uint64_t input_x = 2;
    sigmoid.run(input_x);
    return 0;
}
