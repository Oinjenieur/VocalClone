"""
Module for voice recording and audio manipulation.

This module provides an interface for recording, visualizing, and manipulating
audio data, with integration of volume detection, waveform display,
and audio file import/export.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QSlider, QPushButton, QComboBox, QFileDialog,
                              QGroupBox, QSplitter, QProgressBar, QSizePolicy,
                              QCheckBox, QMessageBox, QDialog, QLineEdit, QMainWindow,
                              QDialogButtonBox, QScrollArea)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QByteArray, QBuffer, QIODevice, QRect, QPoint, QMetaObject, QThread
from PySide6.QtGui import (QPainter, QPen, QColor, QLinearGradient, QPainterPath, 
                          QBrush, QPolygon)

import pyaudio
import wave
import numpy as np
import os
import time
import librosa
from scipy.io import wavfile
import sounddevice as sd
import soundfile as sf
import threading

# Import the model manager
from core.voice_cloning import model_manager

try:
    from PySide6.QtCore import Q_ARG
except ImportError:
    # Define Q_ARG manually if not available
    def Q_ARG(type_name, value):
        return type_name, value


class WaveformVisualizer(QWidget):
    """Widget to visualize audio waveform"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.audio_data = np.zeros(1000)  # Empty audio data by default
        self.playback_position = 0  # Current playback position
        self.setStyleSheet("background-color: #1a1a1a;")
        
        # Enhanced visual parameters
        self.gradient_start = QColor(30, 100, 255)  # Light blue
        self.gradient_end = QColor(64, 200, 255)    # Blue-cyan
        self.playback_color = QColor(255, 80, 80)   # Red-orange
        self.grid_color = QColor(50, 50, 50, 120)
        
        # Animation data
        self.animation_offset = 0
        
        # Cache for optimization
        self.cached_width = -1
        self.cached_height = -1
        self.cached_points = None
        self.data_version = 0  # Data version counter
        
        # Mutex to avoid concurrency issues
        self.data_lock = threading.RLock()
        
        # Timer for animation created directly here
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(50)  # 20 FPS
        
    def set_audio_data(self, data):
        """Set audio data to visualize"""
        if data is None or len(data) == 0:
            return
            
        # Acquire lock before modifying data
        with self.data_lock:
            # Normalize data if not already normalized
            if np.max(np.abs(data)) > 2.0:  # Probably not normalized
                data = data.astype(np.float32) / 32768.0
                
            # Copy data to avoid reference issues
            self.audio_data = data.copy()
            self.data_version += 1  # Invalidate cache
            self.cached_width = -1  # Force cache update
            
        # Force refresh
        self.update()
        
    def set_playback_position(self, position):
        """Set current playback position"""
        # Acquire lock before modifying position
        with self.data_lock:
            self.playback_position = max(0.0, min(1.0, position))  # Limit between 0 and 1
            
        # Force refresh
        QTimer.singleShot(0, self.update)
        
    def resizeEvent(self, event):
        """Handle widget resizing"""
        super().resizeEvent(event)
        
        # Acquire lock before modifying cache
        with self.data_lock:
            # Invalidate cache on resize
            self.cached_width = -1
            
    def _prepare_waveform_points(self, width, height):
        """Prepare waveform points (cached for optimization)"""
        # Acquire lock before accessing cache
        with self.data_lock:
            # Check if we can use the cache
            if (width == self.cached_width and height == self.cached_height and 
                self.cached_points is not None):
                return self.cached_points
                
            # Check that audio data is valid
            if len(self.audio_data) < 2:
                # Insufficient data, create horizontal line at center
                center_y = height // 2
                points_top = [QPoint(i, center_y) for i in range(width)]
                points_bottom = [QPoint(i, center_y) for i in range(width-1, -1, -1)]
                all_points = points_top + points_bottom
                return all_points
                
            # Calculate step to sample data
            step = max(1, len(self.audio_data) // width)
            center_y = height // 2
            
            # Points for upper path
            points_top = []
            for i in range(width):
                idx = min(int(i * step), len(self.audio_data) - 1)
                value = self.audio_data[idx]
                y = center_y - int(value * (height / 2 - 8))
                points_top.append(QPoint(i, y))
                
            # Points for lower path (mirror)
            points_bottom = []
            for i in range(width-1, -1, -1):
                idx = min(int(i * step), len(self.audio_data) - 1)
                value = self.audio_data[idx]
                y = center_y + int(value * (height / 2 - 8))
                points_bottom.append(QPoint(i, y))
                
            # Cache results
            all_points = points_top + points_bottom
            self.cached_width = width
            self.cached_height = height
            self.cached_points = all_points
            
            return all_points

    def closeEvent(self, event):
        """Clean up when closing the widget"""
        if self.update_timer and self.update_timer.isActive():
            self.update_timer.stop()
        super().closeEvent(event)
        
    def paintEvent(self, event):
        """Draw the audio waveform"""
        # Acquire lock before accessing data
        try:
            with self.data_lock:
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing)
                
                width = self.width()
                height = self.height()
                
                # Draw background
                background = QLinearGradient(0, 0, 0, height)
                background.setColorAt(0, QColor(22, 22, 26))
                background.setColorAt(1, QColor(16, 16, 20))
                painter.fillRect(0, 0, width, height, background)
                
                # Draw subtle grid
                painter.setPen(QPen(self.grid_color, 1, Qt.DotLine))
                
                # Horizontal lines
                for i in range(1, 4):
                    y = height * (i / 4)
                    painter.drawLine(0, y, width, y)
                    
                # Vertical lines (less frequent for optimization)
                for i in range(1, 5):
                    x = width * (i / 5)
                    painter.drawLine(x, 0, x, height)
                
                # Center line
                painter.setPen(QPen(QColor(70, 70, 80), 1))
                painter.drawLine(0, height // 2, width, height // 2)
                
                # Calculate waveform points (with caching)
                waveform_points = self._prepare_waveform_points(width, height)
                
                # Create complete path
                path = QPainterPath()
                path.addPolygon(QPolygon(waveform_points))
                
                # Set gradient with animation
                self.animation_offset = (self.animation_offset + 1) % 360
                gradient = QLinearGradient(0, 0, width, 0)
                angle = self.animation_offset / 360 * 6.28
                color1 = QColor(self.gradient_start)
                color2 = QColor(self.gradient_end)
                
                brightness = 0.8 + 0.2 * np.sin(angle)
                color1.setAlphaF(0.7 * brightness)
                color2.setAlphaF(0.7 * brightness)
                
                gradient.setColorAt(0, color1)
                gradient.setColorAt(1, color2)
                
                # Fill the waveform
                painter.fillPath(path, gradient)
                
                # Draw outline with thinner line for optimization
                painter.setPen(QPen(QColor(120, 180, 255, 150), 1.0))
                painter.drawPath(path)
                
                # Draw playback position if > 0
                if self.playback_position > 0.001:  # Avoid values too close to zero
                    position_x = int(self.playback_position * width)
                    
                    # Animated line
                    playback_pen = QPen(self.playback_color, 2)
                    painter.setPen(playback_pen)
                    painter.drawLine(position_x, 0, position_x, height)
                    
                    # Position indicator
                    indicator_size = 8
                    indicator_rect = QRect(position_x - indicator_size/2, 0, indicator_size, indicator_size)
                    painter.setBrush(QBrush(self.playback_color))
                    painter.drawEllipse(indicator_rect)
                    
                    # Progress text
                    progress_text = f"{int(self.playback_position * 100)}%"
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)
                    painter.setPen(QPen(QColor(255, 255, 255, 220)))
                    painter.drawText(position_x + 8, indicator_size * 2, progress_text)
        except Exception as e:
            print(f"Error drawing waveform: {e}")
        finally:
            # Ensure painter is properly ended
            if 'painter' in locals() and painter.isActive():
                painter.end()
                
    def __del__(self):
        """Destructor to clean up resources"""
        try:
            if hasattr(self, 'update_timer'):
                self.update_timer = None
        except Exception as e:
            print(f"Error cleaning up WaveformVisualizer: {e}")


class VUMeter(QWidget):
    """Widget to display a VU meter"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(40, 120)
        self.level = 0.0           # Current level (0.0 - 1.0)
        self.peak = 0.0            # Peak level (0.0 - 1.0)
        self.smoothed_level = 0.0  # Smoothed level for more fluid animation
        
        # Timer for peak decay (created on main thread)
        self.peak_hold_timer = QTimer()
        self.peak_hold_timer.timeout.connect(self._decay_peak)
        self.peak_hold_timer.start(800)  # Peak decay after 800ms
        
        # Timer for visual update
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(33)  # ~30 FPS
        
    def set_level(self, level):
        """Set current level (0.0 - 1.0)"""
        level = min(1.0, max(0.0, level))
        self.level = level
        
        # Smoothing for more fluid animation
        self.smoothed_level = self.smoothed_level * 0.7 + level * 0.3
        
        if level > self.peak:
            self.peak = level
            
        # Use QTimer.singleShot to trigger update in a thread-safe way
        QTimer.singleShot(0, self.update)
        
    def _decay_peak(self):
        """Gradually decay peak level"""
        self.peak = max(0.0, self.peak - 0.05)
        QTimer.singleShot(0, self.update)
        
    def closeEvent(self, event):
        """Clean up when closing the widget"""
        if hasattr(self, 'peak_hold_timer') and self.peak_hold_timer:
            if self.peak_hold_timer.isActive():
                self.peak_hold_timer.stop()
                
        if hasattr(self, 'update_timer') and self.update_timer:
            if self.update_timer.isActive():
                self.update_timer.stop()
                
        super().closeEvent(event)
        
    def __del__(self):
        """Destructor to clean up resources"""
        try:
            if hasattr(self, 'peak_hold_timer'):
                self.peak_hold_timer = None
            if hasattr(self, 'update_timer'):
                self.update_timer = None
        except Exception as e:
            print(f"Error cleaning up VUMeter: {e}")

    def paintEvent(self, event):
        """Draw the VU meter"""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            width = self.width()
            height = self.height()
            
            # Draw background with gradient
            background = QLinearGradient(0, 0, 0, height)
            background.setColorAt(0, QColor(22, 22, 26))
            background.setColorAt(1, QColor(16, 16, 20))
            painter.fillRect(0, 0, width, height, background)
            
            # Calculate meter dimensions
            meter_width = width - 8
            meter_height = height - 8
            
            # Draw frame with 3D effect
            frame_gradient = QLinearGradient(0, 0, width, height)
            frame_gradient.setColorAt(0, QColor(50, 50, 60))
            frame_gradient.setColorAt(1, QColor(35, 35, 45))
            
            painter.setPen(QPen(QColor(70, 70, 80), 1))
            painter.setBrush(QBrush(frame_gradient))
            painter.drawRoundedRect(2, 2, meter_width + 2, meter_height + 2, 4, 4)
            
            # Inner area
            painter.fillRect(4, 4, meter_width - 2, meter_height - 2, QColor(20, 20, 25))
            
            # Draw graduation marks
            painter.setPen(QPen(QColor(80, 80, 100, 100), 1))
            
            # Level reference points (dB)
            db_points = [0.0, 0.12, 0.25, 0.37, 0.5, 0.63, 0.75, 0.88, 1.0]
            
            for level_point in db_points:
                y_pos = int(4 + (meter_height - 4) - level_point * (meter_height - 8))
                painter.drawLine(5, y_pos, meter_width, y_pos)
            
            # Draw current level with gradient
            if self.smoothed_level > 0:
                level_height = int(self.smoothed_level * (meter_height - 8))
                
                # Color gradient based on level
                gradient = QLinearGradient(0, height, 0, 0)
                gradient.setColorAt(0.0, QColor(0, 210, 0))    # Green at bottom
                gradient.setColorAt(0.65, QColor(220, 220, 0))  # Yellow in middle
                gradient.setColorAt(0.8, QColor(240, 130, 0))  # Orange
                gradient.setColorAt(1.0, QColor(255, 30, 30))   # Red at top
                
                # Rectangle with rounded corners for level
                level_rect = QRect(5, height - 4 - level_height, meter_width - 4, level_height)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(gradient))
                painter.drawRoundedRect(level_rect, 2, 2)
                
                # Highlight effect
                highlight = QLinearGradient(0, 0, width, 0)
                highlight.setColorAt(0.0, QColor(255, 255, 255, 80))
                highlight.setColorAt(0.5, QColor(255, 255, 255, 40))
                highlight.setColorAt(1.0, QColor(255, 255, 255, 10))
                
                painter.setBrush(QBrush(highlight))
                painter.drawRoundedRect(level_rect, 2, 2)
            
            # Draw peak level with glow effect
            if self.peak > 0:
                peak_y = height - 4 - int(self.peak * (meter_height - 8))
                
                # Determine peak color based on level
                if self.peak > 0.8:
                    peak_color = QColor(255, 60, 60)  # Red
                elif self.peak > 0.65:
                    peak_color = QColor(255, 160, 0)  # Orange
                else:
                    peak_color = QColor(220, 220, 0)  # Yellow
                    
                # Peak line with glow effect
                glow_pen = QPen(peak_color, 2)
                painter.setPen(glow_pen)
                painter.drawLine(4, peak_y, width - 4, peak_y)
                
                # Indicator dot on peak line
                painter.setBrush(QBrush(peak_color))
                painter.drawEllipse(width - 8, peak_y - 2, 4, 4)
                
                # Display dB value for high levels
                if self.peak > 0.5:
                    # Convert linear value to approximate dB
                    db_value = int(20 * np.log10(self.peak) + 3)  # +3 to compensate
                    db_text = f"{db_value} dB"
                    
                    font = painter.font()
                    font.setPointSize(7)
                    painter.setFont(font)
                    
                    text_width = painter.fontMetrics().horizontalAdvance(db_text)
                    text_x = (width - text_width) / 2
                    
                    # Semi-transparent text background
                    text_rect = QRect(int(text_x) - 2, peak_y - 14, text_width + 4, 12)
                    painter.fillRect(text_rect, QColor(0, 0, 0, 150))
                    
                    # Text
                    painter.setPen(QPen(peak_color.lighter(130)))
                    painter.drawText(int(text_x), peak_y - 4, db_text)
        except Exception as e:
            print(f"Error drawing VU meter: {e}")
        finally:
            if 'painter' in locals() and painter.isActive():
                painter.end() 


class AudioRecorder(QWidget):
    """Main widget for audio recording"""
    
    recording_changed = Signal(bool)  # Signal emitted when recording state changes
    playback_changed = Signal(bool)   # Signal emitted when playback state changes
    voice_cloned = Signal(str)        # Signal emitted when a voice is successfully cloned
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Basic configuration
        self.audio_data = None  # Recorded audio data
        self.sample_rate = 44100  # Default sample rate
        self.is_recording = False
        self.is_playing = False
        self.record_thread = None
        self.play_thread = None
        self.audio = pyaudio.PyAudio()
        self.current_file_path = None  # Current file path
        self.input_level = 0.0  # Audio input level
        
        # Chunk size for recording
        self.record_chunk_size = 1024  # Default size
        
        # Configure interface
        self.setup_ui()
        
        # Initialize audio devices
        self._update_audio_devices()
        
        # Timer to update interface
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_ui)
        self.update_timer.start(50)  # 20 FPS
        
    def setup_ui(self):
        """Initialize user interface"""
        main_layout = QVBoxLayout(self)
        
        # Audio device selection
        devices_group = QGroupBox("Audio Devices")
        devices_layout = QVBoxLayout(devices_group)
        
        # Audio input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input:"))
        self.input_combo = QComboBox()
        input_layout.addWidget(self.input_combo)
        devices_layout.addLayout(input_layout)
        
        # Audio output
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output:"))
        self.output_combo = QComboBox()
        output_layout.addWidget(self.output_combo)
        devices_layout.addLayout(output_layout)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._update_audio_devices)
        devices_layout.addWidget(refresh_button)
        
        main_layout.addWidget(devices_group)
        
        # Central visualization (waveform)
        self.waveform = WaveformVisualizer()
        main_layout.addWidget(self.waveform, 1)  # Stretch factor 1
        
        # Recording duration display
        duration_layout = QHBoxLayout()
        self.duration_label = QLabel("Duration: 00:00")
        self.duration_label.setAlignment(Qt.AlignCenter)
        duration_layout.addWidget(self.duration_label)
        main_layout.addLayout(duration_layout)
        
        # Volume and speed controls
        controls_group = QGroupBox("Controls")
        controls_group_layout = QHBoxLayout(controls_group)
        
        # Input VU meter
        self.vu_meter_input = VUMeter()
        controls_group_layout.addWidget(self.vu_meter_input)
        
        # Input volume fader
        input_vol_layout = QVBoxLayout()
        input_vol_layout.addWidget(QLabel("Input"))
        self.input_volume = QSlider(Qt.Vertical)
        self.input_volume.setRange(0, 100)
        self.input_volume.setValue(100)
        input_vol_layout.addWidget(self.input_volume)
        controls_group_layout.addLayout(input_vol_layout)
        
        # Output volume fader
        output_vol_layout = QVBoxLayout()
        output_vol_layout.addWidget(QLabel("Output"))
        self.output_volume = QSlider(Qt.Vertical)
        self.output_volume.setRange(0, 100)
        self.output_volume.setValue(80)
        output_vol_layout.addWidget(self.output_volume)
        controls_group_layout.addLayout(output_vol_layout)
        
        # Playback speed fader
        speed_layout = QVBoxLayout()
        speed_layout.addWidget(QLabel("Speed"))
        self.playback_speed = QSlider(Qt.Vertical)
        self.playback_speed.setRange(50, 150)
        self.playback_speed.setValue(100)  # 100% = normal speed
        self.playback_speed.setTickPosition(QSlider.TicksRight)
        self.playback_speed.setTickInterval(10)
        speed_layout.addWidget(self.playback_speed)
        
        # Speed value display
        self.speed_label = QLabel("1.0x")
        self.speed_label.setAlignment(Qt.AlignCenter)
        speed_layout.addWidget(self.speed_label)
        
        # Connect value change
        self.playback_speed.valueChanged.connect(self._update_speed_label)
        
        controls_group_layout.addLayout(speed_layout)
        
        main_layout.addWidget(controls_group)
        
        # Control bar
        controls_layout = QHBoxLayout()
        
        # Transport controls
        self.record_button = QPushButton("⏺")
        self.record_button.setStyleSheet("font-size: 24px; min-width: 40px; min-height: 40px; color: red;")
        self.record_button.clicked.connect(self.toggle_recording)
        controls_layout.addWidget(self.record_button)
        
        self.play_button = QPushButton("▶")
        self.play_button.setStyleSheet("font-size: 24px; min-width: 40px; min-height: 40px;")
        self.play_button.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_button)
        
        self.stop_button = QPushButton("⏹")
        self.stop_button.setStyleSheet("font-size: 24px; min-width: 40px; min-height: 40px;")
        self.stop_button.clicked.connect(self.stop)
        controls_layout.addWidget(self.stop_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        controls_layout.addWidget(self.progress_bar, 1)  # Stretch factor 1
        
        main_layout.addLayout(controls_layout)
        
        # Buttons for import/export and voice cloning
        actions_layout = QHBoxLayout()
        
        self.import_button = QPushButton("Import Audio")
        self.import_button.clicked.connect(self.import_audio)
        actions_layout.addWidget(self.import_button)
        
        self.export_button = QPushButton("Export Audio")
        self.export_button.clicked.connect(self.export_audio)
        actions_layout.addWidget(self.export_button)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_audio)
        actions_layout.addWidget(self.save_button)
        
        self.clone_button = QPushButton("Clone Voice")
        self.clone_button.clicked.connect(self.show_clone_dialog)
        actions_layout.addWidget(self.clone_button)
        
        main_layout.addLayout(actions_layout)
        
    def _update_audio_devices(self):
        """Update the list of audio devices"""
        # Save current selections
        current_input = self.input_combo.currentText()
        current_output = self.output_combo.currentText()
        
        # Clear comboboxes
        self.input_combo.clear()
        self.output_combo.clear()
        
        # Add input devices
        input_devices = []
        output_devices = []
        
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            device_name = device_info["name"]
            
            # Input devices
            if device_info["maxInputChannels"] > 0:
                self.input_combo.addItem(device_name, userData=i)
                input_devices.append(device_name)
                
            # Output devices
            if device_info["maxOutputChannels"] > 0:
                self.output_combo.addItem(device_name, userData=i)
                output_devices.append(device_name)
                
        # Restore previous selections if possible
        if current_input in input_devices:
            self.input_combo.setCurrentText(current_input)
            
        if current_output in output_devices:
            self.output_combo.setCurrentText(current_output)
            
    def _update_ui(self):
        """Update the user interface"""
        # Optimization: limit UI update frequency
        now = time.time()
        if hasattr(self, '_last_ui_update') and now - self._last_ui_update < 0.03:  # Max ~33fps
            return
        self._last_ui_update = now
            
        # Update VU meter based on activity
        if self.is_recording and hasattr(self, 'input_level'):
            # During recording, show real-time input level
            self.vu_meter_input.set_level(self.input_level)
            
            # Ensure record button is in stop mode
            if self.record_button.text() != "⏹":
                self.record_button.setText("⏹")
                
            # Update progress
            if hasattr(self, 'recorded_frames') and self.recorded_frames:
                # Update progress bar to 100% during recording
                # to indicate recording is active
                if self.progress_bar.value() < 100:
                    self.progress_bar.setValue(100)
            
        elif self.is_playing and self.audio_data is not None:
            # During playback, simulate VU meter from audio data
            if hasattr(self, 'playback_position'):
                # Calculate position index
                position = int(self.playback_position * len(self.audio_data))
                
                # Optimization: avoid calculations if position is invalid
                if 0 < position < len(self.audio_data) - 1024:
                    # Calculate level in an optimized way
                    window_size = min(1024, len(self.audio_data) - position)
                    window = self.audio_data[position:position+window_size]
                    
                    # Precalculate absolute values
                    abs_window = np.abs(window)
                    rms_level = np.sqrt(np.mean(np.square(abs_window)))
                    peak_level = np.max(abs_window)
                    
                    # Weighted mix
                    level = 0.6 * rms_level + 0.4 * peak_level
                    
                    # Apply output gain
                    output_gain = self.output_volume.value() / 100.0
                    self.vu_meter_input.set_level(level * output_gain)
                
                # Ensure play button is in pause mode
                if self.play_button.text() != "⏸":
                    self.play_button.setText("⏸")
                    
        else:
            # In inactive mode, natural decay
            self.vu_meter_input.set_level(0)
            
            # Ensure buttons are in the correct state
            if self.is_recording and self.record_button.text() != "⏹":
                self.record_button.setText("⏹")
            elif not self.is_recording and self.record_button.text() != "⏺":
                self.record_button.setText("⏺")
                
            if self.is_playing and self.play_button.text() != "⏸":
                self.play_button.setText("⏸")
            elif not self.is_playing and self.play_button.text() != "▶":
                self.play_button.setText("▶")
                
        # Update progress bar during playback
        if self.is_playing and hasattr(self, 'playback_position'):
            # Calculate percentage progress
            progress = int(self.playback_position * 100)
            
            # Update progress bar if value has changed
            if self.progress_bar.value() != progress:
                self.progress_bar.setValue(progress)
                # Force waveform update if not done elsewhere
                if progress % 10 == 0:  # Every 10%
                    self.waveform.set_playback_position(self.playback_position)
                
        # Check if waveform needs to be updated
        if self.audio_data is not None and not hasattr(self, '_last_waveform_update'):
            self._last_waveform_update = True
            self.waveform.set_audio_data(self.audio_data)
        
    def toggle_recording(self):
        """Start or stop recording"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
            
    def start_recording(self):
        """Start audio recording"""
        if self.is_recording:
            return

        # Reset recording data
        self.audio_stream = None
        self.recorded_frames = []
        self.is_recording = True
        self.recording_changed.emit(True)
        
        # Update user interface
        self.record_button.setText("⏹")
        self.progress_bar.setValue(0)
        self.waveform.set_audio_data(np.zeros(1000))  # Reset waveform
        self.waveform.set_playback_position(0)
        self.vu_meter_input.set_level(0)  # Reset VU meter
        self.duration_label.setText("Duration: 00:00")  # Reset duration
        
        # Update UI immediately
        self._update_ui()
        
        # Check input device
        device_index = self.input_combo.currentData()
        if device_index is None:
            QMessageBox.warning(self, "Error", "No input device selected")
            self.stop_recording()
            return
        
        # Start recording thread
        self.recording_thread = threading.Thread(
            target=self._recording_thread,
            args=(device_index,),
            daemon=True
        )
        self.recording_thread.start()

    def _recording_thread(self, device_index):
        """Audio recording thread"""
        try:
            # Setup audio stream
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                device=device_index,
                channels=1,
                callback=self._audio_callback,
                blocksize=self.record_chunk_size
            )
            
            # Start recording
            with self.audio_stream:
                # Recording loop - callback does the work
                while self.is_recording and self.audio_stream.active:
                    # Wait a bit to avoid CPU overload
                    time.sleep(0.01)
        except Exception as e:
            print(f"Recording error: {e}")
            # Use invokeMethod to access UI thread-safe
            # Don't use Q_ARG but QTimer instead
            QTimer.singleShot(0, lambda error=str(e): self._show_recording_error(error))
        finally:
            # Ensure status is correct
            if self.is_recording:
                # Use QTimer instead of invokeMethod
                QTimer.singleShot(0, self.stop_recording)
                
    def _show_recording_error(self, error_message):
        """Display an error message (called from main thread)"""
        QMessageBox.warning(self, "Recording Error", f"An error occurred: {error_message}")
            
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback called by audio stream for each data block"""
        if status:
            print(f"Status: {status}")
            
        # Add data to buffer
        if indata is not None and len(indata) > 0:
            self.recorded_frames.append(indata.copy())
            
            # Calculate audio level for VU meter
            audio_abs = np.abs(indata)
            # Avoid warning np.mean on empty array
            if len(audio_abs) > 0:
                rms_level = np.sqrt(np.mean(np.square(audio_abs))) / 32768.0
                peak_level = np.max(audio_abs) / 32768.0
                
                # Weighted combination for more natural display
                level = 0.7 * rms_level + 0.3 * peak_level
                self.input_level = min(1.0, level * 1.5)  # Slightly amplify for better visibility
                
                # Update VU meter in a thread-safe way
                QTimer.singleShot(0, lambda lvl=self.input_level: self.vu_meter_input.set_level(lvl))
                
                # Update waveform every 2 blocks
                if len(self.recorded_frames) % 2 == 0:
                    # Get all recorded data so far
                    all_data = np.concatenate(self.recorded_frames)
                    # Limit to 10 seconds max for real-time display
                    display_data = all_data[-int(self.sample_rate * 10):]
                    
                    # Update waveform in main thread
                    self._update_waveform_with_data(display_data)
                    
                    # Calculate duration and update label
                    duration = len(all_data) / self.sample_rate
                    duration_str = f"{int(duration // 60):02d}:{int(duration % 60):02d}"
                    QTimer.singleShot(0, lambda d=duration_str: self.duration_label.setText(f"Duration: {d}"))
            
        # Update interface in main thread
        QTimer.singleShot(0, self._update_ui)

    def stop_recording(self):
        """Stop audio recording"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.recording_changed.emit(False)
        
        # Close recording stream
        if self.audio_stream:
            self.audio_stream.close()
            self.audio_stream = None
            
        # Update user interface
        self.record_button.setText("⏺")
        
        # If there's recorded data, convert to numpy array
        if self.recorded_frames and len(self.recorded_frames) > 0:
            try:
                # Concatenate all recorded frames
                self.audio_data = np.concatenate(self.recorded_frames).flatten()
                
                # Update waveform
                QTimer.singleShot(0, lambda: self.waveform.set_audio_data(self.audio_data))
                QTimer.singleShot(0, lambda: self.waveform.set_playback_position(0))
                
                # Enable buttons
                self.play_button.setEnabled(True)
                self.save_button.setEnabled(True)
                self.clone_button.setEnabled(True)
                self.export_button.setEnabled(True)
                
                # Calculate duration
                duration = len(self.audio_data) / self.sample_rate
                duration_str = f"{int(duration // 60):02d}:{int(duration % 60):02d}"
                self.duration_label.setText(f"Duration: {duration_str}")
                
            except Exception as e:
                print(f"Error finalizing recording: {e}")
                QMessageBox.warning(self, "Error", 
                                 f"Unable to process recorded audio: {e}")
                
        # Reset buffers
        self.recorded_frames = []
        
    def toggle_playback(self):
        """Start or pause audio playback"""
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()
            
    def start_playback(self):
        """Start playback of recorded audio"""
        if self.is_playing or self.audio_data is None:
            return
            
        # Stop recording if in progress
        if self.is_recording:
            self.stop_recording()
            
        # Initialize playback variables
        self.is_playing = True
        self.playback_position = 0
        self.playback_changed.emit(True)
            
        # Update interface
        self.play_button.setText("⏸")
        self.progress_bar.setValue(0)
        
        # Prepare audio data for playback
        # Apply output gain
        output_gain = self.output_volume.value() / 100.0
        
        # Make a copy to avoid modifying the original data
        audio_for_playback = self.audio_data.copy() * output_gain
        
        # Update waveform
        self.waveform.set_audio_data(self.audio_data)  # Use original data for display
        self.waveform.set_playback_position(0)
        
        # Get playback speed
        playback_speed = self.playback_speed.value() / 100.0  # 0.5 to 1.5
        
        # Apply speed change if needed
        resampled_data = audio_for_playback
        
        # Use resampling only if speed is not 1.0
        if abs(playback_speed - 1.0) > 0.01:
            try:
                import librosa
                # Resampling with librosa for high quality result
                resampled_data = librosa.effects.time_stretch(audio_for_playback, rate=1.0/playback_speed)
            except Exception as e:
                print(f"Error during resampling: {e}")
                # In case of error, use original data
                resampled_data = audio_for_playback
        
        # Convert to float32 for compatibility with sounddevice
        playback_data = resampled_data.astype(np.float32)
        
        # Calculate total chunks for progress tracking
        chunk_size = 1024
        self.playback_total_chunks = (len(playback_data) + chunk_size - 1) // chunk_size
        
        # Start playback thread
        self.playback_thread = threading.Thread(
            target=self._playback_thread,
            args=(playback_data, chunk_size, playback_speed),
            daemon=True
        )
        self.playback_thread.start()
        
        # Update user interface
        QMetaObject.invokeMethod(self, "_update_ui", Qt.QueuedConnection)

    def _playback_thread(self, audio_data, chunk_size, playback_speed):
        """Optimized audio playback thread"""
        try:
            # Open output stream
            with sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                callback=None,
                blocksize=chunk_size
            ) as stream:
                # Variables to track progress
                position = 0
                update_counter = 0
                
                # Playback by chunks for better responsiveness
                while self.is_playing and position < len(audio_data):
                    # Check if paused
                    if hasattr(self, 'is_paused') and self.is_paused:
                        time.sleep(0.1)
                        continue
                    
                    # Calculate current chunk size (last chunk may be smaller)
                    current_chunk_size = min(chunk_size, len(audio_data) - position)
                    
                    # Extract audio data for this chunk
                    chunk = audio_data[position:position+current_chunk_size]
                    
                    # Write to audio stream
                    stream.write(chunk)
                    
                    # Update position
                    position += current_chunk_size
                    
                    # Calculate relative position for display
                    chunk_index = position // chunk_size
                    self.playback_position = chunk_index / self.playback_total_chunks
                    
                    # Update waveform and UI periodically
                    update_counter += 1
                    if update_counter >= 5:  # Every 5 chunks
                        update_counter = 0
                        
                        # Use QTimer.singleShot instead of invokeMethod
                        current_pos = self.playback_position
                        QTimer.singleShot(0, lambda pos=current_pos: self._update_playback_ui(pos))
                
                # Finalize playback
                if self.is_playing:
                    # If end reached, mark as finished
                    QTimer.singleShot(0, self._finish_playback)
                    
        except Exception as e:
            print(f"Playback error: {e}")
            # Handle error in main thread with QTimer.singleShot
            error_msg = str(e)
            QTimer.singleShot(0, lambda msg=error_msg: self._show_playback_error(msg))
        finally:
            # Ensure flags are reset even in case of error
            if self.is_playing:
                QTimer.singleShot(0, self._finish_playback)
                
    def _show_playback_error(self, error_message):
        """Display playback error message (thread-safe)"""
        QMessageBox.warning(self, "Playback Error", f"An error occurred: {error_message}")

    def _update_playback_ui(self, position):
        """Update user interface during playback (thread-safe)"""
        # Update playback position
        self.playback_position = position
        
        # Update waveform
        self.waveform.set_playback_position(position)
        
        # Update progress bar
        progress = int(position * 100)
        self.progress_bar.setValue(progress)
        
        # Ensure play button is in pause mode
        if self.play_button.text() != "⏸":
            self.play_button.setText("⏸")

    def _finish_playback(self):
        """Finalize audio playback (thread-safe)"""
        # Reset flags
        self.is_playing = False
        self.playback_changed.emit(False)
        
        # Reset interface
        self.play_button.setText("▶")
        self.progress_bar.setValue(0)
        
        # Reset playback position
        self.playback_position = 0
        self.waveform.set_playback_position(0)
        
        # Update UI
        self._update_ui()
        
    def pause_playback(self):
        """Pause audio playback"""
        if not self.is_playing:
            return
            
        self.is_playing = False
        
        # Wait for playback thread to end
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=1.0)
            self.play_thread = None
            
        # Update interface - switch to play icon
        self.play_button.setText("▶")
        self.playback_changed.emit(False)
        
    def stop(self):
        """Stop recording and playback"""
        if self.is_recording:
            self.stop_recording()
            
        if self.is_playing:
            self.pause_playback()
            
        # Reset playback position
        self.playback_position = 0
        self.progress_bar.setValue(0)
        self.waveform.set_playback_position(0)
        
    def save_audio(self):
        """Save current audio"""
        if self.audio_data is None:
            QMessageBox.warning(self, "Warning", "No audio data to save")
            return
            
        # If a file is already open, save directly
        if self.current_file_path:
            self._save_to_file(self.current_file_path)
        else:
            # Otherwise, ask for a new path
            self.export_audio()
            
    def _save_to_file(self, file_path):
        """Save audio data to a specific file"""
        try:
            # Export based on extension
            ext = os.path.splitext(file_path)[1].lower()
            
            # Apply output gain
            output_gain = self.output_volume.value() / 100.0
            export_data = self.audio_data * output_gain
            
            if ext == '.wav':
                # Convert to int16 for WAV
                export_data_int = (export_data * 32767).astype(np.int16)
                wavfile.write(file_path, self.sample_rate, export_data_int)
            else:
                # Use soundfile for other formats
                sf.write(file_path, export_data, self.sample_rate)
                
            # Update current file path
            self.current_file_path = file_path
            
            QMessageBox.information(self, "Save Successful", 
                                  f"Audio saved successfully to:\n{file_path}")
                                  
        except Exception as e:
            QMessageBox.critical(self, "Save Error", 
                               f"Unable to save audio:\n{str(e)}")

    def import_audio(self):
        """Import an audio file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import audio file", "",
            "Audio files (*.wav *.mp3 *.flac *.ogg);;All files (*.*)"
        )
        
        if not file_path:
            return
            
        try:
            # Load audio file
            audio_data, sample_rate = librosa.load(file_path, sr=None, mono=True)
            
            # Update audio data
            self.audio_data = audio_data
            self.sample_rate = sample_rate
            self.waveform.set_audio_data(audio_data)
            
            # Update current file path
            self.current_file_path = file_path
            
            # Reset interface
            self.stop()
            
            QMessageBox.information(self, "Import Successful", 
                                  f"Audio file imported successfully:\n{os.path.basename(file_path)}")
                                  
        except Exception as e:
            QMessageBox.critical(self, "Import Error", 
                               f"Unable to import audio file:\n{str(e)}")
                               
    def export_audio(self):
        """Export audio data to a file"""
        if self.audio_data is None:
            QMessageBox.warning(self, "Warning", "No audio data to export")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export audio", "audio_export.wav",
            "WAV files (*.wav);;MP3 files (*.mp3);;FLAC files (*.flac)"
        )
        
        if not file_path:
            return
            
        self._save_to_file(file_path)
        
    def show_clone_dialog(self):
        """Show dialog to clone a voice"""
        if self.audio_data is None:
            QMessageBox.warning(self, "Warning", "No audio data to clone")
            return
            
        # Create and show clone dialog
        dialog = CloneVoiceDialog(self)
        if dialog.exec():
            # Cloning succeeded, we have a new model ID
            if dialog.cloned_model_id:
                self.voice_cloned.emit(dialog.cloned_model_id)

    def _update_speed_label(self, value):
        """Update speed label"""
        speed = value / 100.0
        self.speed_label.setText(f"{speed:.1f}x")

    def _update_waveform_with_data(self, data):
        """Update waveform with data (thread-safe)"""
        # Create local copy of data
        data_copy = data.copy().flatten()
        
        # Update waveform in a thread-safe way
        try:
            # Use QTimer.singleShot which is thread-safe
            if self.waveform:
                QTimer.singleShot(0, lambda: self.waveform.set_audio_data(data_copy))
        except Exception as e:
            print(f"Error updating waveform: {e}")
            
    def __del__(self):
        """Destructor to avoid errors"""
        # Clean up all resources safely
        try:
            if hasattr(self, 'update_timer'):
                self.update_timer = None
                
            if hasattr(self, 'audio_stream') and self.audio_stream:
                self.audio_stream = None
                
            if hasattr(self, 'audio') and self.audio:
                try:
                    self.audio.terminate()
                except:
                    pass
                self.audio = None
        except Exception as e:
            print(f"Error cleaning up AudioRecorder: {e}")


class CloneVoiceDialog(QDialog):
    """Dialog to configure voice cloning"""
    
    voice_cloned = Signal(str)  # Signal emitted when a voice is successfully cloned
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Clone a Voice")
        self.setMinimumSize(450, 500)
        
        # Cloning result
        self.cloned_model_id = None
        
        # Get parent recorder
        self.recorder = parent
        
        # Configure interface
        self.setup_ui()
        
    def setup_ui(self):
        """Configure user interface"""
        layout = QVBoxLayout(self)
        
        # Explanatory introduction
        intro_label = QLabel(
            "Create a voice model from your recording.\n"
            "This model can be used for voice synthesis."
        )
        intro_label.setWordWrap(True)
        intro_label.setStyleSheet("font-style: italic; color: #666;")
        layout.addWidget(intro_label)
        
        # Voice name
        name_group = QGroupBox("Voice Name")
        name_layout = QVBoxLayout(name_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter a name for this voice...")
        name_layout.addWidget(self.name_edit)
        
        layout.addWidget(name_group) 
        
        # Model to use
        model_group = QGroupBox("Cloning Engine")
        model_layout = QVBoxLayout(model_group)
        
        # Add explanation about engines
        engine_info = QLabel(
            "Each engine has its advantages:\n"
            "• OpenVoice V2: Balance between quality and speed\n"
            "• Bark: Excellent quality but slower\n"
            "• Coqui TTS: Optimal for limited systems"
        )
        engine_info.setWordWrap(True)
        engine_info.setStyleSheet("font-size: 11px; color: #666;")
        model_layout.addWidget(engine_info)
        
        self.model_combo = QComboBox()
        
        # Add available cloning engines
        self.model_combo.addItem("OpenVoice V2", "openvoice_v2")
        self.model_combo.addItem("Bark", "bark")
        self.model_combo.addItem("Coqui TTS", "coqui_tts")
        
        # Engine description
        self.engine_description = QLabel("")
        self.engine_description.setWordWrap(True)
        self.engine_description.setStyleSheet("font-style: italic; font-size: 11px;")
        
        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(self.engine_description)
        
        layout.addWidget(model_group)
        
        # Advanced options (collapsible)
        self.advanced_group = QGroupBox("Advanced Options")
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        advanced_layout = QVBoxLayout(self.advanced_group)
        
        # Cloning quality
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Quality:"))
        
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 3)
        self.quality_slider.setValue(2)
        self.quality_slider.setTickPosition(QSlider.TicksBelow)
        self.quality_slider.setTickInterval(1)
        self.quality_slider.setFixedWidth(200)
        quality_layout.addWidget(self.quality_slider)
        
        quality_labels = QHBoxLayout()
        quality_labels.addWidget(QLabel("Fast"))
        quality_labels.addStretch()
        quality_labels.addWidget(QLabel("Balanced"))
        quality_labels.addStretch()
        quality_labels.addWidget(QLabel("High Quality"))
        
        advanced_layout.addLayout(quality_layout)
        advanced_layout.addLayout(quality_labels)
        
        # Audio preprocessing
        self.preprocess_check = QCheckBox("Preprocess audio (normalization, silence removal)")
        self.preprocess_check.setChecked(True)
        advanced_layout.addWidget(self.preprocess_check)
        
        # Enhanced multilingual training
        self.multilingual_check = QCheckBox("Enhanced multilingual training (slower)")
        self.multilingual_check.setChecked(False)
        advanced_layout.addWidget(self.multilingual_check)
        
        # Tips for better results 
        tips_label = QLabel(
            "<b>Tips for better results:</b><br>"
            "• Use 10-30 seconds of audio minimum<br>"
            "• Ensure the audio is clear and without noise<br>"
            "• Speak naturally with clear diction<br>"
            "• Avoid long pauses between phrases"
        )
        tips_label.setWordWrap(True)
        tips_label.setStyleSheet("font-size: 11px; background-color: #f0f0f0; padding: 8px;")
        advanced_layout.addWidget(tips_label)
        
        layout.addWidget(self.advanced_group)
        
        # Supported languages
        languages_group = QGroupBox("Supported Languages")
        languages_layout = QVBoxLayout(languages_group)
        
        # Available languages
        all_languages = {
            "fr": "French",
            "en": "English",
            "es": "Spanish",
            "de": "German",
            "it": "Italian",
            "zh": "Chinese",
            "ja": "Japanese",
            "pt": "Portuguese",
            "ru": "Russian",
            "nl": "Dutch",
            "ar": "Arabic"
        }
        
        # Quick language selection
        quick_lang_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setFixedWidth(120)
        self.select_all_btn.clicked.connect(lambda: self.toggle_all_languages(True))
        quick_lang_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.setFixedWidth(120)
        self.deselect_all_btn.clicked.connect(lambda: self.toggle_all_languages(False))
        quick_lang_layout.addWidget(self.deselect_all_btn)
        
        languages_layout.addLayout(quick_lang_layout)
        
        # Scroll area for languages
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(150)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Create checkboxes for each language
        self.language_checkboxes = {}
        for lang_code, lang_name in all_languages.items():
            checkbox = QCheckBox(lang_name)
            checkbox.setObjectName(lang_code)  # Store language code in objectName attribute
            scroll_layout.addWidget(checkbox)
            self.language_checkboxes[lang_code] = checkbox
        
        scroll_area.setWidget(scroll_widget)
        languages_layout.addWidget(scroll_area)
            
        # Update available languages when model changes
        self.model_combo.currentIndexChanged.connect(self.update_available_languages)
        self.model_combo.currentIndexChanged.connect(self.update_engine_description)
        
        layout.addWidget(languages_group)
        
        # Duration info and time estimation
        self.duration_label = QLabel()
        self.duration_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.duration_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Progress message
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        self.clone_button = QPushButton("Clone Voice")
        self.clone_button.clicked.connect(self.clone_voice)
        self.clone_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        buttons_layout.addWidget(self.clone_button)
        
        layout.addLayout(buttons_layout)
        
        # Initialize available languages and duration display
        self.update_available_languages()
        self.update_engine_description()
        self.update_duration_info()
        
    def update_engine_description(self):
        """Update selected engine description"""
        engine_id = self.model_combo.currentData()
        
        descriptions = {
            "openvoice_v2": "Creates a voice that preserves timbre and accent well. "
                           "Good balance between speed and quality.",
            "bark": "Produces very natural voices with good expressiveness. "
                   "Slower but with high quality results.",
            "coqui_tts": "Optimized for limited systems. "
                        "Fast and lightweight, ideal for short phrases."
        }
        
        self.engine_description.setText(descriptions.get(engine_id, ""))
        
    def update_duration_info(self):
        """Update audio duration information"""
        if hasattr(self.recorder, 'audio_data') and self.recorder.audio_data is not None:
            duration = len(self.recorder.audio_data) / self.recorder.sample_rate
            
            # Estimate cloning time based on selected engine
            engine = self.model_combo.currentData()
            quality = self.quality_slider.value()
            
            base_times = {
                "openvoice_v2": 60,  # seconds
                "bark": 180,
                "coqui_tts": 45
            }
            
            # Adjust based on quality
            quality_multiplier = {1: 0.7, 2: 1.0, 3: 1.5}
            
            # Calculate time estimation
            est_time = base_times.get(engine, 60) * quality_multiplier.get(quality, 1.0)
            
            # Adjust based on audio duration
            est_time = est_time * (1 + (duration / 30))  # Longer audio takes more time
            
            # Display duration and estimation
            self.duration_label.setText(
                f"Audio duration: {int(duration // 60)}m {int(duration % 60)}s\n"
                f"Estimated time: {int(est_time // 60)}m {int(est_time % 60)}s"
            )
        else:
            self.duration_label.setText("Audio duration: 0s")
        
    def toggle_all_languages(self, state):
        """Select or deselect all available languages"""
        for checkbox in self.language_checkboxes.values():
            if checkbox.isEnabled():
                checkbox.setChecked(state)
        
    def update_available_languages(self):
        """Update available languages based on selected model"""
        # Get selected model
        engine_id = self.model_combo.currentData()
        
        if engine_id:
            # Get languages supported by this engine
            engine_info = model_manager.get_model_info(engine_id)
            supported_languages = engine_info.get("languages", [])
            
            # Update checkboxes
            for lang_code, checkbox in self.language_checkboxes.items():
                checkbox.setEnabled(lang_code in supported_languages)
                checkbox.setChecked(lang_code in supported_languages)
                
            # Update time estimation
            self.update_duration_info()
                
    def clone_voice(self):
        """Process voice cloning after validation"""
        # Check if a name was entered
        voice_name = self.name_edit.text().strip()
        if not voice_name:
            QMessageBox.warning(self, "Missing Name", "Please enter a name for this voice")
            return
            
        # Get selected engine
        engine_id = self.model_combo.currentData()
        if not engine_id:
            QMessageBox.warning(self, "Missing Engine", "Please select an engine")
            return
            
        # Get selected languages
        selected_languages = []
        for lang_code, checkbox in self.language_checkboxes.items():
            if checkbox.isChecked() and checkbox.isEnabled():
                selected_languages.append(lang_code)
                
        if not selected_languages:
            QMessageBox.warning(self, "Missing Languages", "Please select at least one language")
            return
            
        # Set up progress bar
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Preparing cloning...")
        self.progress_label.setVisible(True)
        
        # Disable buttons during processing
        self.cancel_button.setEnabled(False)
        self.clone_button.setEnabled(False)
        
        # Prepare parameters
        params = {
            "voice_name": voice_name,
            "engine": engine_id,
            "languages": selected_languages,
            "sample_rate": self.recorder.sample_rate,
            "quality": self.quality_slider.value(),
            "preprocess": self.preprocess_check.isChecked(),
            "enhanced_multilingual": self.multilingual_check.isChecked()
        }
        
        # Create QThread instance to handle background cloning
        self.clone_thread = QThread()
        self.clone_worker = CloneWorker(self.recorder.audio_data, params)
        self.clone_worker.moveToThread(self.clone_thread)
        
        # Connect signals
        self.clone_thread.started.connect(self.clone_worker.run)
        self.clone_worker.progress.connect(self.update_progress)
        self.clone_worker.finished.connect(self.on_clone_finished)
        self.clone_worker.error.connect(self.on_clone_error)
        self.clone_worker.finished.connect(self.clone_thread.quit)
        self.clone_worker.finished.connect(self.clone_worker.deleteLater)
        self.clone_thread.finished.connect(self.clone_thread.deleteLater)
        
        # Start thread
        self.clone_thread.start()

    def update_progress(self, value, message):
        """Update progress bar"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        
    def on_clone_finished(self, model_id):
        """Called when cloning completes successfully"""
        self.progress_bar.setValue(100)
        self.progress_label.setText("Cloning completed successfully!")
        
        # Store cloned model ID
        self.cloned_model_id = model_id
        
        # Re-enable buttons
        self.cancel_button.setEnabled(True)
        self.clone_button.setEnabled(True)
        
        # Emit signal with model ID
        self.voice_cloned.emit(model_id)
        
        # Close dialog
        self.accept()
        
    def on_clone_error(self, error_message):
        """Called when an error occurs during cloning"""
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Error: " + error_message)
        self.progress_label.setStyleSheet("color: red;")
        
        # Re-enable buttons
        self.cancel_button.setEnabled(True)
        self.clone_button.setEnabled(True)
        
# Worker for background voice cloning
from PySide6.QtCore import QObject, Signal

class CloneWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, audio_data, params):
        super().__init__()
        self.audio_data = audio_data
        self.params = params
        
    def run(self):
        """Run cloning process in separate thread"""
        try:
            # Use clone_voice method from model manager
            voice_name = self.params["voice_name"]
            engine = self.params["engine"]
            languages = self.params["languages"]
            sample_rate = self.params.get("sample_rate", 44100)
            
            # Callback function to report progress
            def progress_callback(value, message):
                self.progress.emit(value, message)
            
            # Clone voice
            model_id = model_manager.clone_voice(
                self.audio_data, 
                sample_rate, 
                voice_name, 
                engine, 
                languages, 
                progress_callback
            )
            
            # Signal cloning is complete
            self.progress.emit(100, "Cloning complete!")
            self.finished.emit(model_id)
            
        except Exception as e:
            self.error.emit(str(e))


class RecordingTab(QWidget):
    """Main tab for voice recording"""
    
    voice_cloned = Signal(str)  # Signal emitted when a voice is successfully cloned
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configure interface
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title_label = QLabel("Voice Recording")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Recording widget
        self.recorder = AudioRecorder()
        self.recorder.voice_cloned.connect(self._on_voice_cloned)
        layout.addWidget(self.recorder)
        
    def _on_voice_cloned(self, model_id):
        """Handle signal emitted when a voice is cloned"""
        # Propagate signal to main application
        self.voice_cloned.emit(model_id)

def safe_cleanup(obj, timer_attrs):
    """Utility to safely clean up timers"""
    for attr in timer_attrs:
        if hasattr(obj, attr):
            try:
                timer = getattr(obj, attr)
                if timer:
                    # Don't check isActive() as it can cause errors
                    try:
                        setattr(obj, attr, None)
                    except:
                        pass
            except Exception as e:
                print(f"Error cleaning up {attr}: {e}") 