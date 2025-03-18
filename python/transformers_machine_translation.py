import torch
import math

from torch import nn
from transformers import MarianMTModel, MarianTokenizer

"""
This implementation aims to simulate the flow of generation in transformers 
with the example of machine translation using MarianMT model.

Model Card: https://huggingface.co/Helsinki-NLP/opus-mt-en-fr
Local Path: ~/.cache/huggingface/hub/models--Helsinki-NLP--opus-mt-en-fr

Steps in `DirectModelGenerator`
- The `generate` method returns output tokens which need to be de-tokenized to get the translation output.

Steps in `EncoderDecoderGenerator`
- The inference is done using the pre-trained weights in encoder and decoder.
- Each decoder output is concatenated to a result tensor and also passed to next decoder call.
- The generation is terminated as soon as the output token is <EOS>.
- If verbose=true, a separate call is made to log the tensor shapes at each step for shape analysis.
"""

MODEL_NAME = "Helsinki-NLP/opus-mt-en-fr"
torch.manual_seed(43)


class MarianMTGenerator():
    def __init__(self, model_name):
        self.tokenizer = MarianTokenizer.from_pretrained(model_name)
        self.marianMT = MarianMTModel.from_pretrained(model_name)

    def run(self, input):
        tokenized_input = self.tokenize(input)
        output = self.generate(tokenized_input)
        detokenized_output = self.detokenize(output)
        print("Generated Output: ", detokenized_output)

    def tokenize(self, input):
        return self.tokenizer(input, return_tensors="pt")

    def generate(self, tokenized_input):
        raise NotImplementedError()

    def detokenize(self, output):
        return self.tokenizer.decode(output[0], skip_special_tokens=True)


class DirectModelGenerator(MarianMTGenerator):
    def __init__(self):
        super().__init__(MODEL_NAME)

    def generate(self, tokenized_input):
        return self.marianMT.generate(**tokenized_input)


class EncoderDecoderGenerator(MarianMTGenerator):
    def __init__(self, verbose=False):
        super().__init__(MODEL_NAME)

        self.encoder = self.marianMT.model.encoder
        self.decoder = self.marianMT.model.decoder
        self.lm_head = self.marianMT.lm_head

        self.pad_token_id = self.tokenizer.pad_token_id  # pad_token_id = 59513
        self.eos_token_id = self.tokenizer.eos_token_id  # eos_token_id = 0

        self.embed_tokens = self.decoder.embed_tokens
        self.embed_positions = self.decoder.embed_positions

        self.embed_dim = 512
        self.num_heads = 8
        self.head_dim = self.embed_dim // self.num_heads

        self.dropout = 0.1
        self.activation_fn = nn.SiLU()

        self.max_length = 100
        self.verbose = verbose

    def generate(self, tokenized_input):
        if self.verbose:
            input_ids = tokenized_input['input_ids']
            print("Encoder Input: ", input_ids, ", Shape: ", tuple(input_ids.shape))

        encoder_outputs = self.encoder(**tokenized_input)
        encoder_hidden_states = encoder_outputs.last_hidden_state

        input_ids = torch.tensor([[self.pad_token_id]])
        decoder_input_ids = input_ids
        past_key_values = None

        if self.verbose:
            print("Encoder Output: ", tuple(encoder_hidden_states.shape))
            print("\nDecoder Input:  ", decoder_input_ids, ", Shape: ", tuple(decoder_input_ids.shape))

        for i in range(self.max_length):
            if self.verbose:
                self.log_shapes(i, decoder_input_ids, encoder_hidden_states, past_key_values)

            decoder_outputs = self.decoder(input_ids=decoder_input_ids, encoder_hidden_states=encoder_hidden_states,
                                           past_key_values=past_key_values)
            decoder_hidden_states = decoder_outputs.last_hidden_state
            past_key_values = decoder_outputs.past_key_values

            lm_logits = self.lm_head(decoder_hidden_states)
            next_token = torch.argmax(lm_logits[:, -1, :], dim=-1, keepdim=True)

            if self.verbose:
                print("  Logits: ", tuple(lm_logits.shape))

            decoder_input_ids = torch.tensor([[next_token]])
            input_ids = torch.cat([input_ids, next_token], dim=-1)

            if next_token.item() == self.eos_token_id:
                break

        if self.verbose:
            print("\nFinal Output: ", input_ids, ", Shape: ", tuple(input_ids.shape))

        return input_ids

    def log_shapes(self, i, decoder_input_ids, encoder_hidden_states, past_key_values):
        if self.verbose:
            print("Step ", i + 1, ":")

        decoder_layer = self.decoder.layers[0]
        past_key_values = past_key_values[0] if past_key_values is not None else None

        hidden_states = self.log_embedding_shapes(decoder_input_ids, past_key_values)
        hidden_states = self.log_self_attention_shapes(decoder_layer, hidden_states, past_key_values)
        hidden_states = self.log_cross_attention_shapes(decoder_layer, hidden_states, encoder_hidden_states)

        self.log_feed_forward_shapes(decoder_layer, hidden_states)

    def log_embedding_shapes(self, decoder_input_ids, past_key_values):
        if self.verbose:
            print("  Input: ", tuple(decoder_input_ids.shape))

        inputs_embeds = self.embed_tokens(decoder_input_ids) * math.sqrt(self.embed_dim)
        positions_embeds = self.embed_positions(decoder_input_ids.size(),
                                                past_key_values[0][0].shape[2] if past_key_values is not None else 0)

        hidden_states = inputs_embeds + positions_embeds
        hidden_states = nn.functional.dropout(hidden_states, p=self.dropout, training=False)

        if self.verbose:
            print("  Embedding Output: ", tuple(hidden_states.shape))

        return hidden_states

    def log_self_attention_shapes(self, decoder_layer, hidden_states, past_key_value):
        self_attn = decoder_layer.self_attn
        self_attn_layer_norm = decoder_layer.self_attn_layer_norm
        self_attn_past_key_value = past_key_value[:2] if past_key_value is not None else None

        q = self_attn.q_proj(hidden_states) / self.head_dim ** 0.5
        k = self_attn.k_proj(hidden_states).reshape(1, -1, self.num_heads, self.head_dim).transpose(1, 2)
        v = self_attn.v_proj(hidden_states).reshape(1, -1, self.num_heads, self.head_dim).transpose(1, 2)

        if self_attn_past_key_value is not None:
            k = torch.cat([self_attn_past_key_value[0], k], dim=2)
            v = torch.cat([self_attn_past_key_value[1], v], dim=2)

        q = q.reshape(1, 1, self.num_heads, self.head_dim).reshape(self.num_heads, -1, self.head_dim)
        k = k.reshape(self.num_heads, -1, self.head_dim)
        v = v.reshape(self.num_heads, -1, self.head_dim)

        attn_weights = torch.matmul(q, k.transpose(1, 2))
        attn_probs = nn.functional.softmax(attn_weights, dim=-1)
        attn_probs = nn.functional.dropout(attn_probs, p=self.dropout, training=False)

        attn_output = torch.matmul(attn_probs, v)
        attn_output = attn_output.reshape(1, self.num_heads, 1, self.head_dim).transpose(1, 2)
        attn_output = attn_output.reshape(1, 1, self.embed_dim)
        attn_output = self_attn.out_proj(attn_output)

        if self.verbose:
            print("  Self Attention Q: ", tuple(q.shape))
            print("  Self Attention K: ", tuple(k.shape))
            print("  Self Attention V: ", tuple(v.shape))
            print("  Self Attention Output: ", tuple(attn_output.shape))

        attn_output = nn.functional.dropout(attn_output, p=self.dropout, training=False)
        hidden_states += attn_output
        hidden_states = self_attn_layer_norm(hidden_states)

        return hidden_states

    def log_cross_attention_shapes(self, decoder_layer, hidden_states, encoder_hidden_states):
        cross_attn = decoder_layer.encoder_attn
        cross_attn_layer_norm = decoder_layer.encoder_attn_layer_norm

        q = cross_attn.q_proj(hidden_states) / self.head_dim ** 0.5
        k = cross_attn.k_proj(encoder_hidden_states).reshape(1, -1, self.num_heads, self.head_dim).transpose(1, 2)
        v = cross_attn.v_proj(encoder_hidden_states).reshape(1, -1, self.num_heads, self.head_dim).transpose(1, 2)

        q = q.reshape(1, 1, self.num_heads, self.head_dim).reshape(self.num_heads, -1, self.head_dim)
        k = k.reshape(self.num_heads, -1, self.head_dim)
        v = v.reshape(self.num_heads, -1, self.head_dim)

        attn_weights = torch.matmul(q, k.transpose(1, 2))
        attn_probs = nn.functional.softmax(attn_weights, dim=-1)
        attn_probs = nn.functional.dropout(attn_probs, p=self.dropout, training=False)

        attn_output = torch.matmul(attn_probs, v)
        attn_output = attn_output.reshape(1, self.num_heads, 1, self.head_dim).transpose(1, 2)
        attn_output = attn_output.reshape(1, 1, self.embed_dim)
        attn_output = cross_attn.out_proj(attn_output)

        if self.verbose:
            print("  Cross Attention Q: ", tuple(q.shape))
            print("  Cross Attention K: ", tuple(k.shape))
            print("  Cross Attention V: ", tuple(v.shape))
            print("  Cross Attention Output: ", tuple(attn_output.shape))

        attn_output = nn.functional.dropout(attn_output, p=self.dropout, training=False)
        hidden_states += attn_output
        hidden_states = cross_attn_layer_norm(hidden_states)

        return hidden_states

    def log_feed_forward_shapes(self, decoder_layer, hidden_states):
        fc1 = decoder_layer.fc1
        fc2 = decoder_layer.fc2
        final_layer_norm = decoder_layer.final_layer_norm

        residual = hidden_states

        hidden_states = fc1(hidden_states)
        hidden_states = self.activation_fn(hidden_states)

        hidden_states = fc2(hidden_states)
        hidden_states = nn.functional.dropout(hidden_states, p=self.dropout, training=False)

        hidden_states = residual + hidden_states
        hidden_states = final_layer_norm(hidden_states)

        # hidden_states = [ 0.0061, -0.0981, -0.0139,  ..., -0.0170, -0.0444, -0.0092]
        if self.verbose:
            print("  Feed Forward Output: ", tuple(hidden_states.shape))
        return hidden_states


if __name__ == '__main__':
    input_text = "I am going to sleep."
    print("Input text: ", input_text)

    print("\n------------------------")
    print("Direct Model Generation")
    print("------------------------")
    DirectModelGenerator().run(input_text)

    print("\n---------------------------")
    print("Encoder-Decoder Generation")
    print("---------------------------")
    EncoderDecoderGenerator(verbose=True).run(input_text)
