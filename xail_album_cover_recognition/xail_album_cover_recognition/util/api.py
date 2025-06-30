import frappe
from frappe.utils import get_site_name
import torch
import pandas as pd
from PIL import Image
from torchvision import datasets, transforms
import requests
from io import BytesIO

import torch.nn as nn
import torchvision.models as models
import json

loaded_model = None
df_albums = None
transform = None
device = None

def match_album(image_url):
    """
    Match an album using the provided image URL.
    """
    global loaded_model
    global df_albums
    global transform
    global device


    # site_home = get_site_name(frappe.local.request.host)

    # filename = f'./assets/xail_album_cover_recognition/data/popular_vinyl_detailed.xlsx'
    model_filename = './assets/xail_album_cover_recognition/model/resnet50_finetuned.pth'
    mapping_file = './assets/xail_album_cover_recognition/data/class_mapping.json'

    class_dict = {}
    
    with open(mapping_file, 'r') as f:
        class_dict = json.load(f)
    num_classes = len(class_dict)
    class_list = list(class_dict.keys())

    # if df_albums is None:
    #     df_albums = pd.read_excel(filename)
    #     df_albums.fillna(method='ffill', inplace=True)

    if device is None:
        device = torch.device('cpu')

    # Check if the model is already loaded
    if loaded_model is None:
        # loaded_model = torch.load(model_filename, weights_only=False)

        loaded_model = models.resnet50(pretrained=False)
        num_ftrs = loaded_model.fc.in_features

        # Replace the final fully connected layer with a new one for our number of classes
        loaded_model.fc = nn.Linear(num_ftrs, num_classes)

        loaded_model.load_state_dict(torch.load(model_filename, map_location=device, weights_only=True))
        # loaded_model = torch.load(model_filename)
        loaded_model.eval()
    if transform is None:
        transform = transforms.Compose([
            transforms.Resize((150, 150)),  # Optional: Resize if needed
            transforms.ToTensor()            # Converts to tensor and scales to [0, 1]
        ])

    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))

    img_tensor = transform(img)

    img_tensor = img_tensor.unsqueeze(0).to(device)  # Now shape is (1, C, H, W)

    with torch.no_grad():
            output = loaded_model(img_tensor)
            probabilities = torch.softmax(output, dim=1)
            topk_probs, topk_indices = torch.topk(probabilities, k=5, dim=1)
            # _, top5_indices = torch.topk(output, 5, dim = 1)
            # predicted_index = predicted_index.item()
            # top5_indices = top5_indices.squeeze().tolist()  # shape [5]
            topk_probs_list = topk_probs.squeeze().tolist()
            topk_indices_list = topk_indices.squeeze().tolist()

    topk_class_names = [class_list[idx] for idx in topk_indices_list]
        
    # Return the lists of indices, names, and probabilities
    return list(zip(topk_class_names, topk_probs_list))



    # for key in class_dict:
    #     if class_dict[key] == pred_class:
    #         print('CLOSEST IMAGE MATCH:')
    #         print(df_albums.loc[df_albums['ID (Release Code)'] == key].iloc[0])
    #         return df_albums.loc[df_albums['ID (Release Code)'] == key].iloc[0]


@frappe.whitelist(allow_guest=True)
def search_album(image_url):
    """
    Search for an album using the provided image URL.
    """
    # Validate the input
    if not image_url:
        return {"error": "Image is required."}

    # Call the search_album function from the AlbumCoverRecognition class
    try:
        result = match_album(image_url)
        return result
    except Exception as e:
        return {"error": str(e)}