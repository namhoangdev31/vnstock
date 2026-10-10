import { useForm } from '@tanstack/react-form';

import * as React from 'react';
import { Animated, StyleSheet, View } from 'react-native';
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as z from 'zod';

import { Button, Input, Text } from '@/components/ui';
import { getFieldError } from '@/components/ui/form-utils';

const schema = z.object({
  email: z
    .string({ message: 'Email là bắt buộc' })
    .min(1, 'Email là bắt buộc')
    .email('Định dạng email không hợp lệ'),
  password: z
    .string({ message: 'Mật khẩu là bắt buộc' })
    .min(1, 'Mật khẩu là bắt buộc')
    .min(6, 'Mật khẩu tối thiểu 6 ký tự'),
});

export type FormType = z.infer<typeof schema>;

export type LoginFormProps = {
  onSubmit?: (data: FormType) => void;
};

function LoginBrand() {
  return (
    <View style={styles.header}>
      <View style={styles.logoContainer}>
        <Text style={styles.logoText}>V</Text>
      </View>
      <Text style={styles.brandName}>Vnstock Terminal</Text>
    </View>
  );
}

function LoginTitle() {
  return (
    <View style={styles.titleSection}>
      <Text style={styles.title}>Đăng nhập</Text>
      <Text style={styles.subtitle}>
        Demo — nhập bất kỳ email và mật khẩu để tiếp tục
      </Text>
    </View>
  );
}

export function LoginForm({ onSubmit = () => {} }: LoginFormProps) {
  const fadeAnim = React.useRef(new Animated.Value(0)).current;
  const slideAnim = React.useRef(new Animated.Value(24)).current;

  React.useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.spring(slideAnim, { toValue: 0, tension: 80, friction: 12, useNativeDriver: true }),
    ]).start();
  }, [fadeAnim, slideAnim]);

  const form = useForm({
    defaultValues: { email: '', password: '' },
    validators: { onChange: schema as any },
    onSubmit: async ({ value }) => { onSubmit(value); },
  });

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior="padding" keyboardVerticalOffset={10}>
      <SafeAreaView style={{ flex: 1 }}>
        <View style={styles.container}>
          <View style={styles.bgAccent} />
          <Animated.View
            style={[styles.content, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}
          >
            <LoginBrand />
            <LoginTitle />
            <View style={styles.formSection}>
              <form.Field
                name="email"
                children={field => (
                  <Input
                    testID="email-input"
                    label="Email"
                    value={field.state.value}
                    onBlur={field.handleBlur}
                    onChangeText={field.handleChange}
                    error={getFieldError(field)}
                    keyboardType="email-address"
                    autoCapitalize="none"
                    autoComplete="email"
                  />
                )}
              />
              <form.Field
                name="password"
                children={field => (
                  <Input
                    testID="password-input"
                    label="Mật khẩu"
                    placeholder="••••••"
                    secureTextEntry={true}
                    value={field.state.value}
                    onBlur={field.handleBlur}
                    onChangeText={field.handleChange}
                    error={getFieldError(field)}
                    autoComplete="password"
                  />
                )}
              />
              <form.Subscribe
                selector={state => [state.isSubmitting]}
                children={([isSubmitting]) => (
                  <Button testID="login-button" label="Đăng nhập" onPress={form.handleSubmit} loading={isSubmitting} />
                )}
              />
            </View>
          </Animated.View>
        </View>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0E14',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  bgAccent: {
    position: 'absolute',
    bottom: -100,
    left: -80,
    width: 280,
    height: 280,
    borderRadius: 140,
    backgroundColor: 'rgba(255, 108, 0, 0.06)',
  },
  content: { gap: 32 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  logoContainer: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: '#FF6C00',
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoText: { color: '#fff', fontSize: 20, fontWeight: '800' },
  brandName: { color: '#ffffff', fontSize: 15, fontWeight: '700' },
  titleSection: { gap: 8 },
  title: { color: '#ffffff', fontSize: 32, fontWeight: '800', letterSpacing: -0.5 },
  subtitle: { color: '#737373', fontSize: 14, lineHeight: 22 },
  formSection: { gap: 4 },
});
