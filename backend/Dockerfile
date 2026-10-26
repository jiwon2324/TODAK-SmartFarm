# 1단계: Gradle 빌드 (테스트는 별도 단계에서 실행)
FROM gradle:8.10.2-jdk21 AS build
WORKDIR /app
COPY build.gradle settings.gradle ./
COPY gradle ./gradle
RUN gradle dependencies -q > /dev/null 2>&1 || true
COPY src ./src
RUN gradle bootJar -x test -q

# 2단계: 실행
FROM eclipse-temurin:21-jre
ENV TZ=Asia/Seoul
WORKDIR /app
RUN useradd -r -u 1001 todak
COPY --from=build /app/build/libs/*.jar app.jar
USER todak
EXPOSE 8080
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=60", "-jar", "app.jar"]
