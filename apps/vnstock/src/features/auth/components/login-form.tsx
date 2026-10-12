import type { AnyFieldApi } from '@tanstack/react-form';
import { useForm } from '@tanstack/react-form';
import { useRouter } from 'expo-router';
import * as React from 'react';
import { ActivityIndicator } from 'react-native';
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as z from 'zod';

import {
  Button,
  Image,
  Input,
  Pressable,
  ScrollView,
  Text,
  View,
} from '@/components/ui';
import { getFieldError } from '@/components/ui/form-utils';
import { Apple, Eye, EyeOff, Google } from '@/components/ui/icons';

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
  onCancel?: () => void;
  initialMode?: 'signIn' | 'signUp';
  onGoogleSelect?: () => void;
  onAppleSelect?: () => void;
  loadingProvider?: 'google' | 'apple' | null;
};

function AuthHeader({ onCancel }: { onCancel: () => void }) {
  return (
    <View className="h-12 w-full flex-row items-center justify-between px-6">
      <Pressable
        hitSlop={8}
        className="py-2 active:opacity-70"
        onPress={onCancel}
      >
        <Text className="text-base font-normal text-coinbase-blue">Cancel</Text>
      </Pressable>
    </View>
  );
}

function AuthTitle({ mode }: { mode: 'signIn' | 'signUp' }) {
  const isSignIn = mode === 'signIn';
  return (
    <View className="mb-6 px-6">
      <Image
        source={require('../../../../assets/vistock-logo-blue.png')}
        className="mb-4 h-9 w-10"
        contentFit="contain"
        placeholder={null}
      />
      <Text
        testID="form-title"
        className="text-display/9 font-bold tracking-tight text-midnight dark:text-pure-white"
      >
        {isSignIn ? 'Sign in to ViStock' : 'Create your ViStock account'}
      </Text>
      <Text className="mt-2 text-body/5 text-slate">
        {isSignIn
          ? 'Not your device? Use a private or incognito window to sign in.'
          : 'Start researching and trading quantitative financial markets.'}
      </Text>
    </View>
  );
}

function PasswordField({
  field,
  showPassword,
  onTogglePassword,
  isSignIn,
}: {
  field: AnyFieldApi;
  showPassword: boolean;
  onTogglePassword: () => void;
  isSignIn: boolean;
}) {
  return (
    <>
      <View className="relative">
        <Input
          testID="password-input"
          label="Password"
          placeholder="••••••••"
          secureTextEntry={!showPassword}
          value={field.state.value}
          onBlur={field.handleBlur}
          onChangeText={field.handleChange}
          error={getFieldError(field)}
          autoComplete="password"
        />

        <Pressable
          hitSlop={8}
          className="absolute top-9.5 right-3.5 z-10"
          onPress={onTogglePassword}
        >
          {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
        </Pressable>
      </View>

      {isSignIn && (
        <Pressable className="mb-4 self-start active:opacity-70">
          <Text className="text-sm font-medium text-coinbase-blue">
            Forgot password?
          </Text>
        </Pressable>
      )}
    </>
  );
}

function FormInputs({
  form,
  mode,
  showPassword,
  setShowPassword,
}: {

  form: any;
  mode: 'signIn' | 'signUp';
  showPassword: boolean;
  setShowPassword: React.Dispatch<React.SetStateAction<boolean>>;
}) {
  return (
    <>
      <form.Field name="email">
        { }
        {(field: any) => (
          <Input
            testID="email-input"
            label="Email"
            placeholder="Your email address"
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
        { }
        {(field: any) => (
          <PasswordField
            field={field}
            showPassword={showPassword}
            onTogglePassword={() => setShowPassword(prev => !prev)}
            isSignIn={mode === 'signIn'}
          />
        )}
      </form.Field>
    </>
  );
}

function SocialAuthSection({
  mode = 'signIn',
  onGoogleSelect,
  onAppleSelect,
  loadingProvider,
}: {
  mode?: 'signIn' | 'signUp';
  onGoogleSelect?: () => void;
  onAppleSelect?: () => void;
  loadingProvider?: 'google' | 'apple' | null;
}) {
  const isSignIn = mode === 'signIn';
  const isLoading = loadingProvider != null;

  return (
    <View className="w-full gap-3">
      <View className="my-3 flex-row items-center">
        <View className="h-px flex-1 bg-pewter dark:bg-white/10" />
        <Text className="px-3 text-xs font-semibold text-slate">OR</Text>
        <View className="h-px flex-1 bg-pewter dark:bg-white/10" />
      </View>

      <Pressable
        testID="google-login-button"
        disabled={isLoading}
        className="h-12 w-full flex-row items-center justify-center gap-3 rounded-full border border-pewter bg-pure-white active:bg-frost"
        onPress={onGoogleSelect}
      >
        {loadingProvider === 'google'
          ? (
              <ActivityIndicator size="small" color="#0A0B0D" />
            )
          : (
              <>
                <Google size={20} />
                <Text className="text-body font-semibold text-midnight">
                  {isSignIn ? 'Sign in with Google' : 'Sign up with Google'}
                </Text>
              </>
            )}
      </Pressable>

      <Pressable
        testID="apple-login-button"
        disabled={isLoading}
        className="h-12 w-full flex-row items-center justify-center gap-3 rounded-full bg-cloud active:bg-pewter"
        onPress={onAppleSelect}
      >
        {loadingProvider === 'apple'
          ? (
              <ActivityIndicator size="small" color="#0A0B0D" />
            )
          : (
              <>
                <Apple size={20} color="#0A0B0D" />
                <Text className="text-body font-semibold text-midnight">
                  {isSignIn ? 'Sign in with Apple' : 'Sign up with Apple'}
                </Text>
              </>
            )}
      </Pressable>
    </View>
  );
}

function ModeToggle({
  mode,
  onToggle,
}: {
  mode: 'signIn' | 'signUp';
  onToggle: () => void;
}) {
  const isSignIn = mode === 'signIn';
  return (
    <View className="mt-6 flex-row items-center justify-center">
      <Text className="text-sm text-slate">
        {isSignIn ? 'Don\'t have an account? ' : 'Already have an account? '}
      </Text>
      <Pressable hitSlop={8} onPress={onToggle}>
        <Text className="text-sm font-semibold text-coinbase-blue underline">
          {isSignIn ? 'Create free account' : 'Sign in'}
        </Text>
      </Pressable>
    </View>
  );
}

function LegalFootnote() {
  return (
    <Text className="mt-8 text-center text-xs/5 text-ash">
      We use strictly necessary cookies to enable essential functions, such as
      security and authentication. For more information, see our Privacy Policy
      and Terms of Service.
    </Text>
  );
}

export function LoginForm({
  onSubmit = () => {},
  onCancel,
  initialMode = 'signIn',
  onGoogleSelect,
  onAppleSelect,
  loadingProvider,
}: LoginFormProps) {
  const router = useRouter();
  const [mode, setMode] = React.useState<'signIn' | 'signUp'>(initialMode);
  const [showPassword, setShowPassword] = React.useState(false);

  const handleCancel = React.useCallback(() => {
    if (onCancel) {
      onCancel();
    }
    else if (router.canGoBack()) {
      router.back();
    }
    else {
      router.replace('/onboarding');
    }
  }, [onCancel, router]);

  const form = useForm({
    defaultValues: { email: '', password: '' },
    validators: { onChange: schema },
    onSubmit: async ({ value }) => {
      onSubmit(value);
    },
  });

  return (
    <KeyboardAvoidingView className="flex-1 bg-pure-white" behavior="padding" keyboardVerticalOffset={10}>
      <SafeAreaView className="flex-1" edges={['top', 'bottom']}>
        <AuthHeader onCancel={handleCancel} />

        <ScrollView className="flex-1" showsVerticalScrollIndicator={false}>
          <AuthTitle mode={mode} />

          <View className="px-6 pb-6">
            <FormInputs
              form={form}
              mode={mode}
              showPassword={showPassword}
              setShowPassword={setShowPassword}
            />

            <form.Subscribe selector={state => [state.isSubmitting]}>
              {([isSubmitting]) => (
                <Button
                  testID="login-button"
                  label={mode === 'signIn' ? 'Continue' : 'Create account'}
                  className="mt-2 h-13 rounded-full bg-coinbase-blue active:opacity-85"
                  textClassName="text-[17px] font-semibold text-pure-white"
                  onPress={form.handleSubmit}
                  loading={isSubmitting}
                />
              )}
            </form.Subscribe>

            <SocialAuthSection
              mode={mode}
              onGoogleSelect={onGoogleSelect}
              onAppleSelect={onAppleSelect}
              loadingProvider={loadingProvider}
            />

            <ModeToggle
              mode={mode}
              onToggle={() => setMode(prev => (prev === 'signIn' ? 'signUp' : 'signIn'))}
            />

            <LegalFootnote />
          </View>
        </ScrollView>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}
