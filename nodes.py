import ollama
from ollama import Client
from tqdm import tqdm
from PIL import Image
from io import BytesIO

class LlavaDescriber:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "optional": {
              "run_mode": (["Local (Ollama)", "API (Ollama)"],),
              "api_host": ("STRING", {
                  "default": "http://localhost:11434"
              })  
            },
            "required": {
                "image": ("IMAGE",),  
                "model": (["llava:7b-v1.6", "llava:13b-v1.6", "llava:34b-v1.6"],),
                "prompt": ("STRING", {
                    "default": "Return a list of danbooru tags for this image, formatted as lowercase, separated by commas.",
                    "multiline": True
                }),
                "temperature": ("FLOAT", {
                    "min": 0,
                    "max": 1,
                    "step": 0.1,
                    "default": 0.2
                }),
                "max_tokens": ("INT", {
                    "step": 10,
                    "default": 200
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("description",)

    FUNCTION = "process_image"

    OUTPUT_NODE = True

    CATEGORY = "image"

    def tensor_to_image(self, tensor):
        tensor = tensor.cpu()
    
        image_np = tensor.squeeze().mul(255).clamp(0, 255).byte().numpy()
    
        image = Image.fromarray(image_np, mode='RGB')
        return image
    
    def pull_model(self, model, client):
        current_digest, bars = '', {}
        for progress in client.pull(model, stream=True):
            digest = progress.get('digest', '')
            if digest != current_digest and current_digest in bars:
                bars[current_digest].close()

            if not digest:
                print(progress.get('status'))
                continue

            if digest not in bars and (total := progress.get('total')):
                bars[digest] = tqdm(total=total, desc=f'pulling {digest[7:19]}', unit='B', unit_scale=True)

            if completed := progress.get('completed'):
                bars[digest].update(completed - bars[digest].n)

            current_digest = digest
  
  
    def process_image(self, image, model, prompt, temperature, max_tokens, run_mode, api_host):
        print('Converting Tensor to Image')
        img = self.tensor_to_image(image)
        
        print('Converting Image to Bytes')
        with BytesIO() as buffer:
            img.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
        
        print('Generating Annotation from Image')
        full_response = ""
        
        system_context = """You are an assistant who describes the content and composition of images. 
        Describe only what you see in the image, not what you think the image is about.Be factual and literal. 
        Do not use metaphors or similes. Be concise.
        """
        
        print(run_mode)
        
        if run_mode == "Local (Ollama)":
            models = [model_l['name'] for model_l in ollama.list()['models']]
             
            if model not in models:
                self.pull_model(model, ollama)
                
            full_response = ollama.generate(model=model, system=system_context, prompt=prompt, images=[image_bytes], stream=False, keep_alive=0, options={
                 'num_predict': max_tokens,
                 'temperature': temperature,
            })
        else:
            client = Client(api_host, timeout=30)
            models = [model_l['name'] for model_l in client.list()['models']]
            
            if model not in models:
                self.pull_model(model, client)
                
            full_response = client.generate(model=model, system=system_context, prompt=prompt, images=[image_bytes], stream=False, options={
                 'num_predict': max_tokens,
                 'temperature': temperature,
            })
            
        print('Finalizing')
        return (full_response['response'], )

    #@classmethod
    #def IS_CHANGED(s, image, string_field, int_field, float_field, print_to_screen):
    #    return ""


# Set the web directory, any .js file in that directory will be loaded by the frontend as a frontend extension
# WEB_DIRECTORY = "./somejs"

# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "LLaVaDescriber": LlavaDescriber
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "LLaVaDescriber": "🌋 LLaVa Describer by Alisson 🦙"
}
