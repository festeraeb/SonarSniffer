"""
Colormap utilities for sonar data visualization
"""
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.cm as cm

def get_available_colormaps():
    """Get list of available colormaps"""
    return [
        'viridis', 'plasma', 'inferno', 'magma', 'cividis',
        'turbo', 'hot', 'cool', 'spring', 'summer', 'autumn', 'winter',
        'jet', 'rainbow', 'hsv', 'twilight', 'twilight_shifted',
        'copper', 'bone', 'gray', 'pink', 'seismic', 'RdYlBu'
    ]

def apply_colormap(gray_image, colormap_name='viridis', enhance_contrast=True):
    """
    Apply colormap to grayscale image
    
    Args:
        gray_image: PIL Image in mode 'L' or numpy array
        colormap_name: Name of matplotlib colormap
        enhance_contrast: Whether to enhance contrast before applying colormap
        
    Returns:
        PIL Image in RGB mode with colormap applied
    """
    # Convert to numpy array if needed
    if isinstance(gray_image, Image.Image):
        img_array = np.array(gray_image)
    else:
        img_array = gray_image.copy()
    
    # Ensure it's 2D
    if len(img_array.shape) == 3:
        img_array = img_array[:, :, 0]  # Take first channel
    
    # Enhance contrast if requested
    if enhance_contrast:
        # Stretch histogram to full range
        img_min, img_max = img_array.min(), img_array.max()
        if img_max > img_min:
            img_array = ((img_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
    
    # Normalize to 0-1 range for colormap
    normalized = img_array.astype(np.float32) / 255.0
    
    # Apply colormap
    try:
        cmap = cm.get_cmap(colormap_name)
        colored = cmap(normalized)
        
        # Convert to RGB (remove alpha channel if present)
        if colored.shape[-1] == 4:
            colored = colored[:, :, :3]
        
        # Convert back to 0-255 range
        colored_uint8 = (colored * 255).astype(np.uint8)
        
        # Convert to PIL Image
        return Image.fromarray(colored_uint8, mode='RGB')
        
    except Exception as e:
        print(f"Warning: Failed to apply colormap '{colormap_name}': {e}")
        # Fallback to grayscale
        return Image.fromarray(img_array, mode='L').convert('RGB')

def create_colormap_preview(width=256, height=32, colormap_name='viridis'):
    """Create a preview strip of the colormap"""
    # Create gradient from 0 to 255
    gradient = np.linspace(0, 255, width).astype(np.uint8)
    gradient = np.tile(gradient, (height, 1))
    
    # Apply colormap
    preview_img = apply_colormap(gradient, colormap_name, enhance_contrast=False)
    return preview_img

def enhance_sonar_contrast(img_array, method='histogram_stretch'):
    """
    Enhance contrast for sonar data visualization
    
    Args:
        img_array: 2D numpy array of sonar data
        method: Enhancement method ('histogram_stretch', 'adaptive', 'gamma')
        
    Returns:
        Enhanced numpy array
    """
    if method == 'histogram_stretch':
        # Stretch histogram to full range
        img_min, img_max = img_array.min(), img_array.max()
        if img_max > img_min:
            return ((img_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
        return img_array
    
    elif method == 'adaptive':
        # Adaptive histogram equalization (simplified)
        from scipy.ndimage import uniform_filter
        try:
            # Local mean
            local_mean = uniform_filter(img_array.astype(np.float32), size=50)
            # Local std
            local_sq_mean = uniform_filter(img_array.astype(np.float32)**2, size=50)
            local_std = np.sqrt(local_sq_mean - local_mean**2)
            
            # Normalize using local statistics
            enhanced = (img_array - local_mean) / (local_std + 1e-6) * 50 + 128
            return np.clip(enhanced, 0, 255).astype(np.uint8)
        except:
            # Fallback to histogram stretch
            return enhance_sonar_contrast(img_array, 'histogram_stretch')
    
    elif method == 'gamma':
        # Gamma correction for sonar data (gamma = 0.5 brightens shadows)
        gamma = 0.5
        normalized = img_array.astype(np.float32) / 255.0
        corrected = np.power(normalized, gamma) * 255
        return np.clip(corrected, 0, 255).astype(np.uint8)
    
    return img_array

def create_dual_colormap(left_img, right_img, left_colormap='hot', right_colormap='cool', gap=8):
    """
    Apply different colormaps to left and right images and combine them
    
    Args:
        left_img: PIL Image or numpy array for left side
        right_img: PIL Image or numpy array for right side
        left_colormap: Colormap for left side
        right_colormap: Colormap for right side
        gap: Gap between images in pixels
        
    Returns:
        Combined PIL Image in RGB mode
    """
    # Apply colormaps
    left_colored = apply_colormap(left_img, left_colormap)
    right_colored = apply_colormap(right_img, right_colormap)
    
    # Ensure same height
    left_array = np.array(left_colored)
    right_array = np.array(right_colored)
    
    height = max(left_array.shape[0], right_array.shape[0])
    
    # Resize if needed
    if left_array.shape[0] != height:
        left_colored = left_colored.resize((left_array.shape[1], height), Image.Resampling.LANCZOS)
        left_array = np.array(left_colored)
    
    if right_array.shape[0] != height:
        right_colored = right_colored.resize((right_array.shape[1], height), Image.Resampling.LANCZOS)
        right_array = np.array(right_colored)
    
    # Create combined image
    total_width = left_array.shape[1] + right_array.shape[1] + gap
    combined = np.zeros((height, total_width, 3), dtype=np.uint8)
    
    # Place left image
    combined[:, :left_array.shape[1]] = left_array
    
    # Place right image
    combined[:, left_array.shape[1] + gap:] = right_array
    
    return Image.fromarray(combined, mode='RGB')

def get_colormap_category(colormap_name):
    """Get category of colormap for UI organization"""
    perceptual = ['viridis', 'plasma', 'inferno', 'magma', 'cividis']
    sequential = ['turbo', 'hot', 'cool', 'copper', 'bone', 'gray', 'pink']
    diverging = ['seismic', 'RdYlBu', 'coolwarm', 'bwr']
    cyclic = ['hsv', 'twilight', 'twilight_shifted']
    qualitative = ['spring', 'summer', 'autumn', 'winter', 'jet', 'rainbow']
    
    if colormap_name in perceptual:
        return 'Perceptual'
    elif colormap_name in sequential:
        return 'Sequential'
    elif colormap_name in diverging:
        return 'Diverging'
    elif colormap_name in cyclic:
        return 'Cyclic'
    elif colormap_name in qualitative:
        return 'Qualitative'
    else:
        return 'Other'