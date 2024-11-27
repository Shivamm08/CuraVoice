import os
from flask import Flask, render_template, request, jsonify
import torch
import re
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments, pipeline
from trl import SFTTrainer
from peft import LoraConfig
from datasets import load_dataset
from deep_translator import GoogleTranslator
from gtts import gTTS

# Initialize Flask app
app = Flask(__name__)

# Step 1: Loading the Model
model_dir = 'E:/LLM_Model/Model_Downloaded_2'

llama_model = AutoModelForCausalLM.from_pretrained(
    pretrained_model_name_or_path=model_dir,
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=getattr(torch, "float16"), bnb_4bit_quant_type="nf4")
)

llama_model.config.use_cache = False
llama_model.config.pretraining_tp = 1

llama_tokenizer = AutoTokenizer.from_pretrained(
    pretrained_model_name_or_path=model_dir, trust_remote_code=True
)

llama_tokenizer.pad_token = llama_tokenizer.eos_token
llama_tokenizer.padding_side = "right"

# Step 2: Setting Training Arguments
training_arguments = TrainingArguments(
    output_dir="./results",  # Results will be saved locally
    per_device_train_batch_size=1,
    max_steps=1  # Training for 1 step only
)

# Track whether the model has already been trained
model_trained = False

# Step 3: Creating the Fine-Tuning Trainer
def train_model():
    global model_trained
    if model_trained:
        print("Model has already been trained. Skipping training.")
        return
    print("Starting model training...")
    
    train_dataset = load_dataset(path="aboonaji/wiki_medical_terms_llam2_format", split="train")
    peft_config = LoraConfig(task_type="CAUSAL_LM", r=64, lora_alpha=16, lora_dropout=0.1)
    llama_sft_trainer = SFTTrainer(
        model=llama_model,
        args=training_arguments,  # Pass the correct TrainingArguments object
        train_dataset=train_dataset,
        tokenizer=llama_tokenizer,
        peft_config=peft_config,
        dataset_text_field="text"
    )
    
    llama_sft_trainer.train()
    print("Model training complete.")
    model_trained = True

# Step 4: Chatting with the Model (Text + Voice)
def generate_response(user_prompt, target_language="en"):
    try:
        # Translate the input to English using deep-translator
        translated_input = GoogleTranslator(source=target_language, target='en').translate(user_prompt)

        # Generate response using the trained model
        text_generation_pipeline = pipeline(
            task="text-generation", model=llama_model, tokenizer=llama_tokenizer, max_length=500
        )
        model_answer = text_generation_pipeline(f"[INST] {translated_input} [/INST]")

        if model_answer and 'generated_text' in model_answer[0]:
            generated_text = model_answer[0]['generated_text']
            cleaned_text = re.sub(r'\[INST\].*?\[/INST\]', '', generated_text).strip()

            # Translate the response back to the target language
            translated_response = GoogleTranslator(source='en', target=target_language).translate(cleaned_text)

            # Convert response to speech using Google TTS
            tts = gTTS(text=translated_response, lang=target_language)
            audio_file = 'static/output_audio.mp3'  # Save the audio file
            tts.save(audio_file)

            return translated_response, audio_file
        else:
            return "No response from model", None

    except Exception as e:
        return str(e), None

# Flask route to generate response
@app.route('/chat', methods=['POST'])
def chat():
    user_prompt = request.json['prompt']
    target_language = request.json['language']
    response, audio_file = generate_response(user_prompt, target_language)
    
    if response is None or audio_file is None:
        return jsonify({'error': 'Failed to generate response'}), 500
    
    return jsonify({'response': response, 'audio': f'/{audio_file}'})

# Flask route for the main page
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    # Check if the Flask app is running with the reloader or not
    if not os.environ.get('WERKZEUG_RUN_MAIN'):  # Prevent the model from reloading in debug mode
        train_model()  # Train the model before starting the Flask app
    
    # Start Flask with the reloader disabled to prevent multiple reloads
    app.run(debug=True, use_reloader=False)  # Disable the reloader
