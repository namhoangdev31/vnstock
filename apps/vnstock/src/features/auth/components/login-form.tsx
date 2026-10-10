import { useForm } from '@tanstack/react-form';
import * as React from 'react';
import { Animated } from 'react-native';
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as z from 'zod';

import { Button, Input, Text, View } from '@/components/ui';
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
    <View className="flex-row items-center gap-2.5">
      <View className="size-10 items-center justify-center rounded-[10px] bg-aave-violet">
        <Text className="text-xl font-extrabold text-aave-charcoal">V</Text>
      </View>
      <Text className="text-[15px] font-bold text-aave-paper">Vnstock Terminal</Text>
    </View>
  );
}

function LoginTitle() {
  return (
    <View className="gap-2">
      <Text testID="form-title" className="text-3xl font-extrabold tracking-tight text-aave-paper">Đăng nhập</Text>
      <Text className="text-sm/5.5 text-aave-graphite">
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
    validators: { onChange: schema },
    onSubmit: async ({ value }) => {
      onSubmit(value);
    },
  });

  return (
    <KeyboardAvoidingView className="flex-1" behavior="padding" keyboardVerticalOffset={10}>
      <SafeAreaView className="flex-1">
        <View className="relative flex-1 justify-center bg-aave-inkwell px-6">
          <View className="absolute -bottom-25 -left-20 size-70 rounded-full bg-aave-violet/6" />
          <Animated.View
            className="gap-8"
            style={{ opacity: fadeAnim, transform: [{ translateY: slideAnim }] }}
          >
            <LoginBrand />
            <LoginTitle />
            <View className="gap-1">
              <form.Field name="email">
                {field => (
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
              </form.Field>
              <form.Field name="password">
                {field => (
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
              </form.Field>
              <form.Subscribe selector={state => [state.isSubmitting]}>
                {([isSubmitting]) => (
                  <Button
                    testID="login-button"
                    label="Đăng nhập"
                    onPress={form.handleSubmit}
                    loading={isSubmitting}
                  />
                )}
              </form.Subscribe>
            </View>
          </Animated.View>
        </View>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}
