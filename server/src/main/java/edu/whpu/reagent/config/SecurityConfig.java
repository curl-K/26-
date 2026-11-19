package edu.whpu.reagent.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
public class SecurityConfig {

    @Bean
    PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    DeviceTokenFilter deviceTokenFilter(@Value("${device.token}") String token) {
        return new DeviceTokenFilter(token);
    }

    @Bean
    FilterRegistrationBean<DeviceTokenFilter> deviceTokenRegistration(DeviceTokenFilter filter) {
        FilterRegistrationBean<DeviceTokenFilter> registration = new FilterRegistrationBean<>(filter);
        registration.setEnabled(false);
        return registration;
    }

    @Bean
    AuthenticationManager authenticationManager(AuthenticationConfiguration configuration) throws Exception {
        return configuration.getAuthenticationManager();
    }

    @Bean
    SecurityFilterChain filterChain(HttpSecurity http, DeviceTokenFilter deviceTokenFilter) throws Exception {
        http.csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(HttpMethod.POST, "/auth/login").permitAll()
                        .requestMatchers("/device/**").permitAll()
                        .requestMatchers("/actuator/health", "/actuator/health/**").permitAll()
                        .requestMatchers(HttpMethod.GET, "/reagents").authenticated()
                        .requestMatchers(HttpMethod.POST, "/reagents").hasRole("MANAGER")
                        .requestMatchers("/reagents/**").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.GET, "/alarms").authenticated()
                        .requestMatchers(HttpMethod.POST, "/alarms/**").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.GET, "/environment").authenticated()
                        .requestMatchers(HttpMethod.GET, "/accounts").hasRole("MANAGER")
                        .anyRequest().authenticated())
                .exceptionHandling(ex -> ex
                        .authenticationEntryPoint((request, response, error) -> {
                            response.setStatus(401);
                            response.setContentType("application/json;charset=UTF-8");
                            response.getWriter().write("{\"result\":\"unauthorized\",\"message\":\"请先登录\"}");
                        })
                        .accessDeniedHandler((request, response, error) -> {
                            response.setStatus(403);
                            response.setContentType("application/json;charset=UTF-8");
                            response.getWriter().write("{\"result\":\"forbidden\",\"message\":\"没有这项权限\"}");
                        }))
                .addFilterBefore(deviceTokenFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }
}
