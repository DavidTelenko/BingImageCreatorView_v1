import torch
from PIL import Image
from RealESRGAN import RealESRGAN
import sys
from Utils import TimeThis, formatTime
from super_image import EdsrModel, ImageLoader


def printTime(time):
    print(
        f"Upscale took: {time} ns | {formatTime(round(time / 1_000_000))}")


def edsrUpscale(i, o, scale):
    image = Image.open(i)

    model = EdsrModel.from_pretrained('res/models/edsr', scale=scale)
    inputs = ImageLoader.load_image(image)
    preds = model(inputs)

    ImageLoader.save_image(preds, o)


def esrganUpscale(i, o, scale):
    with TimeThis(printTime):
        device_type = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Selected device type: {device_type}")

        device = torch.device(device_type)

        model = RealESRGAN(device, scale=scale)
        model.load_weights(
            f'res/models/RealESRGAN_x4.pth', download=True
        )

        image = Image.open(i).convert('RGB')

        sr_image = model.predict(image)
        sr_image.save(o)


def upscale(i, o, scale=4, method="edsr"):
    methods = {
        "edsr": edsrUpscale,
        "esrgan": esrganUpscale,
    }
    methods[method](i, o, scale)


if __name__ == "__main__":
    i, o = sys.argv[1], sys.argv[2]
    upscale(i, o, 4)
