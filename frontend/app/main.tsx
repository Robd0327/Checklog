import React, { useState, useContext, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  Alert,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  StatusBar,
  ScrollView,
  Image,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import * as Camera from 'expo-camera';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Auth Context Type
interface AuthContextType {
  user: any;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
}

// We'll get the context from props instead of importing to avoid circular dependency
export default function MainScreen({ auth }: { auth: AuthContextType }) {
  const [businessName, setBusinessName] = useState('');
  const [quantitySold, setQuantitySold] = useState('');
  const [checkImage, setCheckImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

  useEffect(() => {
    requestPermissions();
  }, []);

  const requestPermissions = async () => {
    const cameraPermission = await Camera.requestCameraPermissionsAsync();
    const mediaLibraryPermission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (cameraPermission.status !== 'granted' || mediaLibraryPermission.status !== 'granted') {
      Alert.alert(
        'Permissions Required',
        'Camera and photo library access are required to capture check images.',
        [{ text: 'OK' }]
      );
    }
  };

  const showImagePicker = () => {
    Alert.alert(
      'Select Check Image',
      'Choose how you want to add the check image',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Take Photo', onPress: takePhoto },
        { text: 'Choose from Gallery', onPress: pickImage },
      ]
    );
  };

  const takePhoto = async () => {
    try {
      setLoading(true);
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.7,
        base64: true,
      });

      if (!result.canceled && result.assets[0]) {
        const base64 = result.assets[0].base64;
        if (base64) {
          setCheckImage(`data:image/jpeg;base64,${base64}`);
        }
      }
    } catch (error) {
      console.error('Camera error:', error);
      Alert.alert('Camera Error', 'Failed to take photo. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const pickImage = async () => {
    try {
      setLoading(true);
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.7,
        base64: true,
      });

      if (!result.canceled && result.assets[0]) {
        const base64 = result.assets[0].base64;
        if (base64) {
          setCheckImage(`data:image/jpeg;base64,${base64}`);
        }
      }
    } catch (error) {
      console.error('Image picker error:', error);
      Alert.alert('Image Error', 'Failed to select image. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const submitPayment = async () => {
    // Validation
    if (!businessName.trim()) {
      Alert.alert('Missing Information', 'Please enter the business name');
      return;
    }
    
    if (!quantitySold.trim() || isNaN(Number(quantitySold)) || Number(quantitySold) <= 0) {
      Alert.alert('Invalid Quantity', 'Please enter a valid quantity (number greater than 0)');
      return;
    }
    
    if (!checkImage) {
      Alert.alert('Missing Check Image', 'Please take a photo or select an image of the check');
      return;
    }

    try {
      setSubmitting(true);
      
      const token = await AsyncStorage.getItem('auth_token');
      if (!token) {
        Alert.alert('Authentication Error', 'Please log in again');
        auth?.logout();
        return;
      }

      // Remove the data:image/jpeg;base64, prefix for backend
      const base64Data = checkImage.replace(/^data:image\/[a-z]+;base64,/, '');

      const response = await fetch(`${BACKEND_URL}/api/payments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          businessName: businessName.trim(),
          quantitySold: Number(quantitySold),
          checkImageBase64: base64Data,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        Alert.alert(
          'Payment Logged Successfully',
          `Entry ID: ${data.id}\nBusiness: ${data.businessName}\nQuantity: ${data.quantitySold}\n\nEmail notification sent to rob@nwtacticalclean.com`,
          [
            {
              text: 'OK',
              onPress: () => {
                // Clear form
                setBusinessName('');
                setQuantitySold('');
                setCheckImage(null);
              }
            }
          ]
        );
      } else {
        throw new Error(data.detail || 'Failed to submit payment');
      }
    } catch (error) {
      console.error('Submit error:', error);
      Alert.alert('Submission Error', 'Failed to submit payment. Please check your connection and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const clearForm = () => {
    Alert.alert(
      'Clear Form',
      'Are you sure you want to clear all entered data?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: () => {
            setBusinessName('');
            setQuantitySold('');
            setCheckImage(null);
          }
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#1a1a1a" />
      
      {/* Header */}
      <View style={styles.headerSection}>
        <View style={styles.userHeader}>
          <Ionicons name="person-circle" size={32} color="#4CAF50" />
          <View style={styles.userInfo}>
            <Text style={styles.welcomeText}>Welcome, {auth?.user?.username}</Text>
            <Text style={styles.userRole}>Sales Representative</Text>
          </View>
          <TouchableOpacity onPress={auth?.logout} style={styles.logoutButton}>
            <Ionicons name="log-out" size={24} color="#ff4444" />
          </TouchableOpacity>
        </View>
      </View>

      <KeyboardAvoidingView 
        style={styles.keyboardView} 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
          <View style={styles.formContainer}>
            {/* Title */}
            <View style={styles.titleContainer}>
              <Ionicons name="receipt" size={32} color="#4CAF50" />
              <Text style={styles.formTitle}>Log Check Payment</Text>
            </View>

            {/* Business Name Input */}
            <View style={styles.inputSection}>
              <Text style={styles.inputLabel}>Business Name</Text>
              <View style={styles.inputContainer}>
                <Ionicons name="business" size={20} color="#666" style={styles.inputIcon} />
                <TextInput
                  style={styles.textInput}
                  placeholder="Enter business name"
                  placeholderTextColor="#666"
                  value={businessName}
                  onChangeText={setBusinessName}
                  autoCapitalize="words"
                  autoCorrect={false}
                />
              </View>
            </View>

            {/* Quantity Sold Input */}
            <View style={styles.inputSection}>
              <Text style={styles.inputLabel}>Quantity Sold</Text>
              <View style={styles.inputContainer}>
                <Ionicons name="calculator" size={20} color="#666" style={styles.inputIcon} />
                <TextInput
                  style={styles.textInput}
                  placeholder="Enter quantity"
                  placeholderTextColor="#666"
                  value={quantitySold}
                  onChangeText={setQuantitySold}
                  keyboardType="numeric"
                />
              </View>
            </View>

            {/* Check Image Section */}
            <View style={styles.inputSection}>
              <Text style={styles.inputLabel}>Check Image</Text>
              
              {checkImage ? (
                <View style={styles.imageContainer}>
                  <Image source={{ uri: checkImage }} style={styles.checkImage} />
                  <TouchableOpacity
                    style={styles.changeImageButton}
                    onPress={showImagePicker}
                    disabled={loading}
                  >
                    <Ionicons name="camera" size={20} color="#4CAF50" />
                    <Text style={styles.changeImageText}>Change Image</Text>
                  </TouchableOpacity>
                </View>
              ) : (
                <TouchableOpacity
                  style={styles.imagePickerButton}
                  onPress={showImagePicker}
                  disabled={loading}
                >
                  {loading ? (
                    <ActivityIndicator size="small" color="#4CAF50" />
                  ) : (
                    <>
                      <Ionicons name="camera" size={40} color="#4CAF50" />
                      <Text style={styles.imagePickerText}>Take Photo or Select Image</Text>
                      <Text style={styles.imagePickerSubtext}>Tap to capture check image</Text>
                    </>
                  )}
                </TouchableOpacity>
              )}
            </View>

            {/* Action Buttons */}
            <View style={styles.buttonContainer}>
              <TouchableOpacity
                style={styles.clearButton}
                onPress={clearForm}
                disabled={submitting}
              >
                <Ionicons name="refresh" size={20} color="#ff4444" />
                <Text style={styles.clearButtonText}>Clear</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.submitButton, submitting && styles.submitButtonDisabled]}
                onPress={submitPayment}
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <ActivityIndicator size="small" color="#ffffff" style={{ marginRight: 8 }} />
                    <Text style={styles.submitButtonText}>Submitting...</Text>
                  </>
                ) : (
                  <>
                    <Ionicons name="checkmark-circle" size={20} color="#ffffff" />
                    <Text style={styles.submitButtonText}>Submit Payment</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>

            {/* Info Box */}
            <View style={styles.infoBox}>
              <Ionicons name="information-circle" size={20} color="#4CAF50" />
              <Text style={styles.infoText}>
                All entries are automatically saved and an email notification will be sent to the office.
              </Text>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a1a',
  },
  keyboardView: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  headerSection: {
    padding: 20,
    backgroundColor: '#2a2a2a',
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  userHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  userInfo: {
    flex: 1,
    marginLeft: 12,
  },
  welcomeText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  userRole: {
    color: '#999',
    fontSize: 14,
    marginTop: 2,
  },
  logoutButton: {
    padding: 8,
  },
  formContainer: {
    padding: 20,
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 32,
  },
  formTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
    marginLeft: 12,
  },
  inputSection: {
    marginBottom: 24,
  },
  inputLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2a2a2a',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  inputIcon: {
    marginRight: 12,
  },
  textInput: {
    flex: 1,
    color: '#ffffff',
    fontSize: 16,
  },
  imageContainer: {
    alignItems: 'center',
  },
  checkImage: {
    width: 280,
    height: 200,
    borderRadius: 12,
    backgroundColor: '#2a2a2a',
    marginBottom: 12,
  },
  changeImageButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#2a2a2a',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#4CAF50',
  },
  changeImageText: {
    color: '#4CAF50',
    fontSize: 16,
    marginLeft: 8,
  },
  imagePickerButton: {
    backgroundColor: '#2a2a2a',
    borderRadius: 12,
    paddingVertical: 40,
    paddingHorizontal: 20,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#4CAF50',
    borderStyle: 'dashed',
  },
  imagePickerText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '600',
    marginTop: 12,
    textAlign: 'center',
  },
  imagePickerSubtext: {
    color: '#999',
    fontSize: 14,
    marginTop: 4,
    textAlign: 'center',
  },
  buttonContainer: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
  },
  clearButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'transparent',
    borderRadius: 12,
    paddingVertical: 16,
    borderWidth: 2,
    borderColor: '#ff4444',
  },
  clearButtonText: {
    color: '#ff4444',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  submitButton: {
    flex: 2,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    borderRadius: 12,
    paddingVertical: 16,
  },
  submitButtonDisabled: {
    backgroundColor: '#666',
  },
  submitButtonText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  infoBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#2a2a2a',
    padding: 16,
    borderRadius: 8,
    marginTop: 24,
    borderLeftWidth: 3,
    borderLeftColor: '#4CAF50',
  },
  infoText: {
    flex: 1,
    color: '#999',
    fontSize: 14,
    lineHeight: 20,
    marginLeft: 8,
  },
});