import frappe
from frappe.utils import get_site_name
import torch
import pandas as pd
from PIL import Image
from torchvision import datasets, transforms
import requests
from io import BytesIO

import torch.nn as nn
from torchvision.models import vgg16


def match_album(image_url):
    """
    Match an album using the provided image URL.
    """

    # site_home = get_site_name(frappe.local.request.host)

    filename = f'./assets/xail_album_cover_recognition/data/Discogs Data.xlsx'
    train_dir = './assets/xail_album_cover_recognition/data/images'
    model_filename = './assets/xail_album_cover_recognition/model/vgg16_finetuned.pth'

    # Check CUDA availability
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print("CUDA is available. Training on GPU.")
    else:
        device = torch.device("cpu")
        print("CUDA is not available. Training on CPU.")
    

    df_albums = pd.read_excel(filename)
    df_albums.fillna(method='ffill', inplace=True)

    train_dataset = datasets.ImageFolder(train_dir)
    # num_classes = len(train_dataset.class_to_idx)
    # Load the pre-trained VGG16 model

    # model = vgg16(pretrained=True)

    # # Freeze all the layers in the model
    # for param in model.parameters():
    #     param.requires_grad = False

    # model.classifier[6] = nn.Linear(model.classifier[6].in_features, num_classes) 

    loaded_model = torch.load(model_filename, weights_only=False)
    
    transform = transforms.Compose([
        transforms.Resize((150, 150)),  # Optional: Resize if needed
        transforms.ToTensor()            # Converts to tensor and scales to [0, 1]
    ])

    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))

    img_tensor = transform(img)

    img_tensor = img_tensor.unsqueeze(0)  # Now shape is (1, C, H, W)

    with torch.no_grad():
        Prediction= loaded_model.forward(img_tensor.float().to(device))
    print(Prediction)
    pred_class = Prediction.argmax().item()
    print(pred_class)

    class_dict = train_dataset.class_to_idx

    for key in class_dict:
        if class_dict[key] == pred_class:
            print('CLOSEST IMAGE MATCH:')
            print(df_albums.loc[df_albums['ID (Release Code)'] == key].iloc[0])
            return df_albums.loc[df_albums['ID (Release Code)'] == key].iloc[0]


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